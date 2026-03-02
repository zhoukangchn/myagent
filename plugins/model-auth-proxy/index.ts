import { createServer, type IncomingMessage, type ServerResponse } from "node:http";
import { Readable } from "node:stream";
import type {
  OpenClawPluginApi,
  OpenClawPluginService,
  ProviderAuthContext,
  ProviderAuthResult,
} from "openclaw/plugin-sdk";

const PLUGIN_ID = "model-auth-proxy";
const PROVIDER_ID = "internal-model";
const PROVIDER_LABEL = "Internal Model";
const RELAY_PORT = 19429;
const REQUEST_TIMEOUT_MS = 120_000;
const MAX_BODY_BYTES = 8 * 1024 * 1024;
const PLACEHOLDER_API_KEY = "model-auth-proxy";
const DEFAULT_MODEL_IDS = "internal-chat";

const CONTROL_HEADER_UPSTREAM_URL = "x-openclaw-upstream-url";
const CONTROL_HEADER_UPSTREAM_API_KEY = "x-openclaw-upstream-api-key";
const CONTROL_HEADER_CUSTOM_HEADERS = "x-openclaw-upstream-custom-headers";

type HeaderConfig = {
  name: string;
  value: string;
};

type PluginConfig = {
  upstreamUrl?: string;
  apiKey?: string;
  header1?: HeaderConfig | null;
  header2?: HeaderConfig | null;
  tlsInsecure?: boolean;
};

type JsonMap = Record<string, unknown>;

function normalizeBaseUrl(raw: string): string {
  const trimmed = raw.trim();
  if (!trimmed) throw new Error("upstreamUrl is required");
  const withScheme = /^https?:\/\//i.test(trimmed) ? trimmed : `https://${trimmed}`;
  const url = new URL(withScheme);
  let path = url.pathname.replace(/\/+$/, "");
  if (!path.endsWith("/v1")) path = `${path}/v1`;
  url.pathname = path;
  url.search = "";
  url.hash = "";
  return url.toString().replace(/\/+$/, "");
}

function parseModelIds(input: string): string[] {
  return Array.from(
    new Set(
      input
        .split(/[\n,]/)
        .map((x) => x.trim())
        .filter(Boolean),
    ),
  );
}

function parseHeaderConfig(raw: unknown, label: string): HeaderConfig | null {
  if (raw == null) return null;
  if (typeof raw !== "object" || Array.isArray(raw)) {
    throw new Error(`${label} must be an object with name/value`);
  }
  const name = String((raw as Record<string, unknown>).name ?? "").trim();
  const value = String((raw as Record<string, unknown>).value ?? "");
  if (!name) throw new Error(`${label}.name is required`);
  return { name, value };
}

function parseObjectJson(input: string, label: string): Record<string, string> {
  let parsed: unknown;
  try {
    parsed = JSON.parse(input);
  } catch {
    throw new Error(`${label} must be valid JSON`);
  }
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error(`${label} must be a JSON object`);
  }
  const out: Record<string, string> = {};
  for (const [k, v] of Object.entries(parsed)) {
    if (!k.trim()) throw new Error(`${label} contains an empty key`);
    if (typeof v !== "string") throw new Error(`${label}.${k} must be a string`);
    out[k] = v;
  }
  return out;
}

function getSingleHeader(req: IncomingMessage, name: string): string | undefined {
  const value = req.headers[name.toLowerCase()];
  if (Array.isArray(value)) return value[0];
  return typeof value === "string" ? value : undefined;
}

function sanitizeForwardHeaders(req: IncomingMessage): Record<string, string> {
  const blocked = new Set([
    "host",
    "connection",
    "content-length",
    CONTROL_HEADER_UPSTREAM_URL,
    CONTROL_HEADER_UPSTREAM_API_KEY,
    CONTROL_HEADER_CUSTOM_HEADERS,
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

function normalizeUpstreamPath(reqUrl: string): string {
  const url = new URL(reqUrl, "http://127.0.0.1");
  let path = url.pathname;
  if (path === "/v1") path = "/";
  else if (path.startsWith("/v1/")) path = path.slice(3);
  return `${path}${url.search}`;
}

function readRequestBody(req: IncomingMessage): Promise<Buffer> {
  return new Promise((resolve, reject) => {
    const chunks: Buffer[] = [];
    let total = 0;

    req.on("data", (chunk: Buffer) => {
      total += chunk.length;
      if (total > MAX_BODY_BYTES) {
        reject(new Error(`request body exceeds ${MAX_BODY_BYTES} bytes`));
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

function createRelayService(params: {
  pluginConfig: PluginConfig | undefined;
  logger: OpenClawPluginApi["logger"];
}): OpenClawPluginService {
  let server: ReturnType<typeof createServer> | null = null;

  const tlsInsecure = params.pluginConfig?.tlsInsecure === true;

  return {
    id: `${PLUGIN_ID}-relay`,
    async start() {
      if (server) return;

      if (tlsInsecure) {
        process.env.NODE_TLS_REJECT_UNAUTHORIZED = "0";
        params.logger.warn(`${PLUGIN_ID}: tlsInsecure=true, TLS verification disabled`);
      }

      server = createServer(async (req, res) => {
        try {
          const method = (req.method || "GET").toUpperCase();
          const upstreamUrlRaw = getSingleHeader(req, CONTROL_HEADER_UPSTREAM_URL);
          const upstreamApiKey = getSingleHeader(req, CONTROL_HEADER_UPSTREAM_API_KEY);
          const customHeadersRaw = getSingleHeader(req, CONTROL_HEADER_CUSTOM_HEADERS);

          if (!upstreamUrlRaw || !upstreamApiKey) {
            writeJson(res, 400, {
              error:
                "Missing relay control headers. Ensure provider auth is configured and plugin config has upstreamUrl/apiKey.",
            });
            return;
          }

          const upstreamBaseUrl = normalizeBaseUrl(upstreamUrlRaw);
          const upstreamPath = normalizeUpstreamPath(req.url || "/");
          const upstreamUrl = new URL(upstreamPath, `${upstreamBaseUrl}/`);

          const customHeaders = customHeadersRaw
            ? parseObjectJson(customHeadersRaw, "custom headers")
            : {};

          const body = ["GET", "HEAD"].includes(method) ? undefined : await readRequestBody(req);

          const forwardHeaders: Record<string, string> = {
            ...sanitizeForwardHeaders(req),
            ...customHeaders,
            authorization: `Bearer ${upstreamApiKey}`,
          };

          const controller = new AbortController();
          const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

          const upstreamResponse = await fetch(upstreamUrl.toString(), {
            method,
            headers: forwardHeaders,
            body,
            signal: controller.signal,
          });
          clearTimeout(timeout);

          res.statusCode = upstreamResponse.status;
          for (const [key, value] of upstreamResponse.headers.entries()) {
            const lower = key.toLowerCase();
            if (lower === "content-length" || lower === "connection" || lower === "transfer-encoding") {
              continue;
            }
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
        server!.listen(RELAY_PORT, "127.0.0.1", () => resolve());
      });

      params.logger.info(`${PLUGIN_ID} relay listening on http://127.0.0.1:${RELAY_PORT}`);
    },
    async stop() {
      if (!server) return;
      await new Promise<void>((resolve) => server!.close(() => resolve()));
      server = null;
    },
  };
}

const plugin = {
  id: PLUGIN_ID,
  name: "Internal Model Auth Proxy",
  description: "Relay internal-model requests to an OpenAI-compatible upstream with API key auth",
  register(api: OpenClawPluginApi) {
    const pluginConfig = (api.pluginConfig as PluginConfig | undefined) ?? undefined;

    api.registerService(
      createRelayService({
        pluginConfig,
        logger: api.logger,
      }),
    );

    api.registerProvider({
      id: PROVIDER_ID,
      label: PROVIDER_LABEL,
      docsPath: "/providers/models",
      auth: [
        {
          id: "api-key-relay",
          label: "API key relay",
          hint: "Use plugin config for upstreamUrl/apiKey and optional extra headers",
          kind: "custom",
          run: async (ctx: ProviderAuthContext): Promise<ProviderAuthResult> => {
            const upstreamUrl = normalizeBaseUrl(pluginConfig?.upstreamUrl ?? "");
            const apiKey = String(pluginConfig?.apiKey ?? "").trim();
            if (!apiKey) {
              throw new Error(
                `Missing plugins.entries.${PLUGIN_ID}.config.apiKey in ~/.openclaw/openclaw.json`,
              );
            }

            const header1 = parseHeaderConfig(pluginConfig?.header1, "header1");
            const header2 = parseHeaderConfig(pluginConfig?.header2, "header2");

            const customHeaders: Record<string, string> = {};
            if (header1) customHeaders[header1.name] = header1.value;
            if (header2) customHeaders[header2.name] = header2.value;

            const modelIdsInput = await ctx.prompter.text({
              message: "Model IDs (comma-separated)",
              initialValue: DEFAULT_MODEL_IDS,
              validate: (value: string) =>
                parseModelIds(value).length > 0 ? undefined : "Enter at least one model id",
            });
            const modelIds = parseModelIds(modelIdsInput);

            const relayBaseUrl = `http://127.0.0.1:${RELAY_PORT}/v1`;

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
                        [CONTROL_HEADER_UPSTREAM_URL]: upstreamUrl,
                        [CONTROL_HEADER_UPSTREAM_API_KEY]: apiKey,
                        [CONTROL_HEADER_CUSTOM_HEADERS]: JSON.stringify(customHeaders),
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
                `Relay endpoint: ${relayBaseUrl}`,
                "Upstream Authorization is injected as Bearer token from plugin config apiKey.",
                "header1/header2 are injected on every upstream request when configured.",
                "Set tlsInsecure=true only for test environments with self-signed certs.",
              ],
            };
          },
        },
      ],
    });
  },
};

export default plugin;
