import { createServer, type IncomingMessage, type ServerResponse } from "node:http";
import { Readable } from "node:stream";
import type {
  OpenClawPluginApi,
  OpenClawPluginService,
  ProviderAuthContext,
  ProviderAuthResult,
} from "openclaw/plugin-sdk";

const PROVIDER_ID = "internal-model";
const PROVIDER_LABEL = "Internal Model";
const PLACEHOLDER_API_KEY = "internal-model-relay";
const DEFAULT_MODEL_IDS = "internal-chat";
const DEFAULT_TARGET_BASE_URL = "https://internal-llm.example.com/v1";
const DEFAULT_RELAY_PORT = 19321;
const DEFAULT_TIMEOUT_MS = 120_000;
const DEFAULT_MAX_BODY_BYTES = 4 * 1024 * 1024;

const CONTROL_HEADER_TARGET = "x-openclaw-target-base-url";
const CONTROL_HEADER_CUSTOM_HEADERS = "x-openclaw-upstream-headers";
const CONTROL_HEADER_BODY_PATCH = "x-openclaw-body-patch";

const RESERVED_BODY_FIELDS = new Set([
  "model",
  "messages",
  "input",
  "tools",
  "tool_choice",
  "stream",
  "max_tokens",
  "response_format",
  "parallel_tool_calls",
]);

type JsonMap = Record<string, unknown>;

type PluginConfig = {
  relayPort?: number;
  tlsInsecure?: boolean;
  requestTimeoutMs?: number;
  maxBodyBytes?: number;
};

function normalizeBaseUrl(raw: string): string {
  const trimmed = raw.trim();
  if (!trimmed) {
    throw new Error("Base URL is required");
  }
  const withScheme = /^https?:\/\//i.test(trimmed) ? trimmed : `https://${trimmed}`;
  const url = new URL(withScheme);
  let pathname = url.pathname.replace(/\/+$/, "");
  if (!pathname.endsWith("/v1")) pathname = `${pathname}/v1`;
  url.pathname = pathname;
  url.search = "";
  url.hash = "";
  return url.toString().replace(/\/+$/, "");
}

function parseModelIds(input: string): string[] {
  const ids = input
    .split(/[\n,]/)
    .map((item) => item.trim())
    .filter(Boolean);
  return Array.from(new Set(ids));
}

function parseObjectJson(input: string, label: string): Record<string, unknown> {
  let parsed: unknown;
  try {
    parsed = JSON.parse(input);
  } catch {
    throw new Error(`${label} must be valid JSON`);
  }
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error(`${label} must be a JSON object`);
  }
  return parsed as Record<string, unknown>;
}

function parseStringMap(input: string, label: string): Record<string, string> {
  const parsed = parseObjectJson(input, label);
  const out: Record<string, string> = {};
  for (const [k, v] of Object.entries(parsed)) {
    if (!k.trim()) {
      throw new Error(`${label} contains an empty key`);
    }
    if (typeof v !== "string") {
      throw new Error(`${label}.${k} must be a string`);
    }
    out[k] = v;
  }
  return out;
}

function validateBodyPatch(bodyPatch: Record<string, unknown>) {
  for (const key of Object.keys(bodyPatch)) {
    if (RESERVED_BODY_FIELDS.has(key)) {
      throw new Error(`bodyPatch cannot override reserved field: ${key}`);
    }
  }
}

function toProviderModel(modelId: string) {
  return {
    id: modelId,
    name: modelId,
    reasoning: false,
    input: ["text"] as Array<"text" | "image">,
    cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 },
    contextWindow: 128000,
    maxTokens: 8192,
  };
}

function readRequestBody(req: IncomingMessage, maxBodyBytes: number): Promise<Buffer> {
  return new Promise((resolve, reject) => {
    const chunks: Buffer[] = [];
    let total = 0;

    req.on("data", (chunk: Buffer) => {
      total += chunk.length;
      if (total > maxBodyBytes) {
        reject(new Error(`request body exceeds maxBodyBytes=${maxBodyBytes}`));
        req.destroy();
        return;
      }
      chunks.push(chunk);
    });

    req.on("end", () => resolve(Buffer.concat(chunks)));
    req.on("error", reject);
  });
}

function writeJson(res: ServerResponse, statusCode: number, payload: JsonMap) {
  const body = Buffer.from(JSON.stringify(payload));
  res.statusCode = statusCode;
  res.setHeader("content-type", "application/json");
  res.setHeader("content-length", String(body.length));
  res.end(body);
}

function getSingleHeader(req: IncomingMessage, name: string): string | undefined {
  const value = req.headers[name.toLowerCase()];
  if (Array.isArray(value)) return value[0];
  return typeof value === "string" ? value : undefined;
}

function sanitizeForwardHeaders(req: IncomingMessage): Record<string, string> {
  const blocked = new Set([
    "host",
    "content-length",
    CONTROL_HEADER_TARGET,
    CONTROL_HEADER_CUSTOM_HEADERS,
    CONTROL_HEADER_BODY_PATCH,
  ]);
  const out: Record<string, string> = {};
  for (const [rawKey, rawVal] of Object.entries(req.headers)) {
    const key = rawKey.toLowerCase();
    if (blocked.has(key)) continue;
    if (typeof rawVal === "string") out[key] = rawVal;
    else if (Array.isArray(rawVal) && rawVal.length > 0) out[key] = rawVal.join(", ");
  }
  return out;
}

function normalizeUpstreamPath(reqPath: string): string {
  const path = reqPath.split("?")[0] || "/";
  if (path.startsWith("/v1/")) return path.slice(3);
  if (path === "/v1") return "/";
  return path;
}

function createRelayService(params: {
  pluginConfig: PluginConfig | undefined;
  logger: OpenClawPluginApi["logger"];
}): OpenClawPluginService {
  let server: ReturnType<typeof createServer> | null = null;

  const relayPort =
    Number.isFinite(params.pluginConfig?.relayPort) && (params.pluginConfig?.relayPort ?? 0) > 0
      ? Number(params.pluginConfig?.relayPort)
      : DEFAULT_RELAY_PORT;
  const requestTimeoutMs =
    Number.isFinite(params.pluginConfig?.requestTimeoutMs) &&
    (params.pluginConfig?.requestTimeoutMs ?? 0) > 0
      ? Number(params.pluginConfig?.requestTimeoutMs)
      : DEFAULT_TIMEOUT_MS;
  const maxBodyBytes =
    Number.isFinite(params.pluginConfig?.maxBodyBytes) && (params.pluginConfig?.maxBodyBytes ?? 0) > 0
      ? Number(params.pluginConfig?.maxBodyBytes)
      : DEFAULT_MAX_BODY_BYTES;
  const tlsInsecure = params.pluginConfig?.tlsInsecure === true;

  return {
    id: "internal-model-relay",
    async start() {
      if (server) return;

      if (tlsInsecure) {
        process.env.NODE_TLS_REJECT_UNAUTHORIZED = "0";
        params.logger.warn(
          "internal-model-auth: tlsInsecure=true, TLS certificate verification is disabled",
        );
      }

      server = createServer(async (req, res) => {
        try {
          if (req.method !== "POST") {
            writeJson(res, 405, { error: "Method Not Allowed" });
            return;
          }

          const targetBaseUrl = getSingleHeader(req, CONTROL_HEADER_TARGET);
          const extraHeadersRaw = getSingleHeader(req, CONTROL_HEADER_CUSTOM_HEADERS);
          const bodyPatchRaw = getSingleHeader(req, CONTROL_HEADER_BODY_PATCH);

          if (!targetBaseUrl || !extraHeadersRaw || !bodyPatchRaw) {
            writeJson(res, 400, {
              error: "Missing relay control headers. Re-run provider auth login to refresh config.",
            });
            return;
          }

          const upstreamHeaders = parseStringMap(extraHeadersRaw, "upstream headers");
          const bodyPatch = parseObjectJson(bodyPatchRaw, "body patch");
          validateBodyPatch(bodyPatch);

          const rawBody = await readRequestBody(req, maxBodyBytes);
          const bodyText = rawBody.toString("utf8");
          const inputBody = parseObjectJson(bodyText, "request body");

          const mergedBody: JsonMap = { ...inputBody, ...bodyPatch };

          const upstreamBase = normalizeBaseUrl(targetBaseUrl);
          const upstreamPath = normalizeUpstreamPath(req.url || "/");
          const upstreamUrl = new URL(upstreamPath, `${upstreamBase}/`);

          const controller = new AbortController();
          const timeout = setTimeout(() => controller.abort(), requestTimeoutMs);

          const forwardHeaders = {
            ...sanitizeForwardHeaders(req),
            ...upstreamHeaders,
            "content-type": "application/json",
          };

          const upstreamResponse = await fetch(upstreamUrl.toString(), {
            method: "POST",
            headers: forwardHeaders,
            body: JSON.stringify(mergedBody),
            signal: controller.signal,
          });
          clearTimeout(timeout);

          res.statusCode = upstreamResponse.status;
          for (const [key, value] of upstreamResponse.headers.entries()) {
            if (key.toLowerCase() === "content-length") continue;
            res.setHeader(key, value);
          }

          if (!upstreamResponse.body) {
            res.end();
            return;
          }

          Readable.fromWeb(upstreamResponse.body as globalThis.ReadableStream<Uint8Array>).pipe(res);
        } catch (err) {
          const message = err instanceof Error ? err.message : String(err);
          writeJson(res, 502, { error: `relay failure: ${message}` });
        }
      });

      await new Promise<void>((resolve, reject) => {
        server!.once("error", reject);
        server!.listen(relayPort, "127.0.0.1", () => resolve());
      });

      params.logger.info(`internal-model-auth relay listening on http://127.0.0.1:${relayPort}`);
    },
    async stop() {
      if (!server) return;
      await new Promise<void>((resolve) => server!.close(() => resolve()));
      server = null;
    },
  };
}

const plugin = {
  id: "internal-model-auth",
  name: "Internal Model Auth Relay",
  description: "Internal model provider with custom header/body injection via local relay",
  register(api: OpenClawPluginApi) {
    api.registerService(
      createRelayService({
        pluginConfig: (api.pluginConfig as PluginConfig | undefined) ?? undefined,
        logger: api.logger,
      }),
    );

    api.registerProvider({
      id: PROVIDER_ID,
      label: PROVIDER_LABEL,
      docsPath: "/providers/models",
      auth: [
        {
          id: "header-body",
          label: "Custom header + body",
          hint: "Configure upstream URL, injected headers, and injected body JSON",
          kind: "custom",
          run: async (ctx: ProviderAuthContext): Promise<ProviderAuthResult> => {
            const upstreamBaseInput = await ctx.prompter.text({
              message: "Internal model upstream base URL",
              initialValue: DEFAULT_TARGET_BASE_URL,
              validate: (value: string) => {
                try {
                  normalizeBaseUrl(value);
                  return undefined;
                } catch (err) {
                  return err instanceof Error ? err.message : "Invalid URL";
                }
              },
            });

            const headersInput = await ctx.prompter.text({
              message: "Custom upstream headers JSON",
              initialValue: '{"x-api-key":"YOUR_TOKEN"}',
              validate: (value: string) => {
                try {
                  parseStringMap(value, "upstream headers");
                  return undefined;
                } catch (err) {
                  return err instanceof Error ? err.message : "Invalid headers JSON";
                }
              },
            });

            const bodyPatchInput = await ctx.prompter.text({
              message: "Custom body patch JSON (top-level keys)",
              initialValue: '{"temperature":0.2}',
              validate: (value: string) => {
                try {
                  const patch = parseObjectJson(value, "body patch");
                  validateBodyPatch(patch);
                  return undefined;
                } catch (err) {
                  return err instanceof Error ? err.message : "Invalid body patch JSON";
                }
              },
            });

            const modelIdsInput = await ctx.prompter.text({
              message: "Model IDs (comma-separated)",
              initialValue: DEFAULT_MODEL_IDS,
              validate: (value: string) =>
                parseModelIds(value).length > 0 ? undefined : "Enter at least one model id",
            });

            const upstreamBaseUrl = normalizeBaseUrl(upstreamBaseInput);
            const upstreamHeaders = parseStringMap(headersInput, "upstream headers");
            const bodyPatch = parseObjectJson(bodyPatchInput, "body patch");
            validateBodyPatch(bodyPatch);
            const modelIds = parseModelIds(modelIdsInput);

            const relayPort =
              Number.isFinite((api.pluginConfig as PluginConfig | undefined)?.relayPort) &&
              ((api.pluginConfig as PluginConfig | undefined)?.relayPort ?? 0) > 0
                ? Number((api.pluginConfig as PluginConfig | undefined)?.relayPort)
                : DEFAULT_RELAY_PORT;
            const relayBaseUrl = `http://127.0.0.1:${relayPort}/v1`;

            return {
              profiles: [
                {
                  profileId: `${PROVIDER_ID}:default`,
                  credential: {
                    type: "token",
                    provider: PROVIDER_ID,
                    token: PLACEHOLDER_API_KEY,
                  },
                },
              ],
              configPatch: {
                models: {
                  providers: {
                    [PROVIDER_ID]: {
                      baseUrl: relayBaseUrl,
                      apiKey: PLACEHOLDER_API_KEY,
                      api: "openai-completions",
                      authHeader: false,
                      headers: {
                        [CONTROL_HEADER_TARGET]: upstreamBaseUrl,
                        [CONTROL_HEADER_CUSTOM_HEADERS]: JSON.stringify(upstreamHeaders),
                        [CONTROL_HEADER_BODY_PATCH]: JSON.stringify(bodyPatch),
                      },
                      models: modelIds.map((modelId) => toProviderModel(modelId)),
                    },
                  },
                },
                agents: {
                  defaults: {
                    models: Object.fromEntries(modelIds.map((modelId) => [`${PROVIDER_ID}/${modelId}`, {}])),
                  },
                },
              },
              defaultModel: `${PROVIDER_ID}/${modelIds[0]}`,
              notes: [
                `Requests are routed through local relay ${relayBaseUrl}.`,
                "Custom headers and body patch are injected by relay before forwarding upstream.",
                "bodyPatch uses shallow merge and cannot override reserved fields (model/messages/input/tools/stream/max_tokens).",
                "If you use self-signed TLS upstream, set plugins.entries.internal-model-auth.config.tlsInsecure=true for testing only.",
              ],
            };
          },
        },
      ],
    });
  },
};

export default plugin;
