import type {
  OpenClawPluginApi,
  ProviderAuthContext,
  ProviderAuthResult,
} from "openclaw/plugin-sdk";

const PLUGIN_ID = "model-auth-proxy";
const PROVIDER_ID = "internal-model";
const PROVIDER_LABEL = "Internal Model";
const DEFAULT_BASE_URL = "https://gateway.company.com/v1";
const DEFAULT_MODEL_IDS = "gpt-4o-mini";

type PluginConfig = {
  tlsInsecure?: boolean;
};

function normalizeBaseUrl(raw: string): string {
  const trimmed = raw.trim();
  if (!trimmed) {
    throw new Error("Upstream base URL is required");
  }
  const withScheme = /^https?:\/\//i.test(trimmed) ? trimmed : `https://${trimmed}`;
  const url = new URL(withScheme);
  const pathname = url.pathname.replace(/\/+$/, "");
  url.pathname = pathname || "/v1";
  url.search = "";
  url.hash = "";
  return url.toString().replace(/\/+$/, "");
}

function parseModelIds(input: string): string[] {
  const ids = input
    .split(/[\n,]/)
    .map((v) => v.trim())
    .filter(Boolean);
  return Array.from(new Set(ids));
}

function parseHeaders(input: string): Record<string, string> {
  const trimmed = input.trim();
  if (!trimmed) return {};

  let parsed: unknown;
  try {
    parsed = JSON.parse(trimmed);
  } catch {
    throw new Error("Custom headers must be valid JSON");
  }

  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error("Custom headers must be a JSON object");
  }

  const out: Record<string, string> = {};
  for (const [key, value] of Object.entries(parsed as Record<string, unknown>)) {
    if (!key.trim()) {
      throw new Error("Custom headers contains an empty key");
    }
    if (typeof value !== "string") {
      throw new Error(`Custom headers.${key} must be a string`);
    }
    out[key] = value;
  }
  return out;
}

function toProviderModel(modelId: string) {
  return {
    id: modelId,
    name: modelId,
    contextWindow: 128000,
    maxTokens: 8192,
  };
}

const plugin = {
  id: PLUGIN_ID,
  name: "Model Auth Proxy",
  description: "Direct provider auth plugin for internal model gateways with custom headers",
  register(api: OpenClawPluginApi) {
    const pluginConfig = (api.pluginConfig as PluginConfig | undefined) ?? undefined;
    if (pluginConfig?.tlsInsecure === true) {
      process.env.NODE_TLS_REJECT_UNAUTHORIZED = "0";
      api.logger.warn(
        "model-auth-proxy: tlsInsecure=true, TLS certificate verification is disabled for this process",
      );
    }

    api.registerProvider({
      id: PROVIDER_ID,
      label: PROVIDER_LABEL,
      docsPath: "/providers/models",
      auth: [
        {
          id: "api-key-headers",
          label: "API key + custom headers",
          hint: "Configure upstream URL, API key, optional custom headers, and model ids",
          kind: "custom",
          run: async (ctx: ProviderAuthContext): Promise<ProviderAuthResult> => {
            const baseUrlInput = await ctx.prompter.text({
              message: "Upstream base URL",
              initialValue: DEFAULT_BASE_URL,
              validate: (value: string) => {
                try {
                  normalizeBaseUrl(value);
                  return undefined;
                } catch (err) {
                  return err instanceof Error ? err.message : "Invalid URL";
                }
              },
            });

            const apiKeyInput = await ctx.prompter.text({
              message: "API key (Bearer token)",
              validate: (value: string) =>
                value.trim().length > 0 ? undefined : "API key is required",
            });

            const headersInput = await ctx.prompter.text({
              message: 'Custom headers JSON (optional, e.g. {"x-tenant-id":"team-a"})',
              initialValue: "{}",
              validate: (value: string) => {
                try {
                  parseHeaders(value);
                  return undefined;
                } catch (err) {
                  return err instanceof Error ? err.message : "Invalid headers JSON";
                }
              },
            });

            const modelIdsInput = await ctx.prompter.text({
              message: "Model IDs (comma-separated)",
              initialValue: DEFAULT_MODEL_IDS,
              validate: (value: string) =>
                parseModelIds(value).length > 0 ? undefined : "Enter at least one model id",
            });

            const baseUrl = normalizeBaseUrl(baseUrlInput);
            const apiKey = apiKeyInput.trim();
            const headers = parseHeaders(headersInput);
            const modelIds = parseModelIds(modelIdsInput);

            return {
              profiles: [
                {
                  profileId: `${PROVIDER_ID}:default`,
                  credential: {
                    type: "token",
                    provider: PROVIDER_ID,
                    token: apiKey,
                  },
                },
              ],
              configPatch: {
                models: {
                  providers: {
                    [PROVIDER_ID]: {
                      baseUrl,
                      apiKey,
                      api: "openai-completions",
                      authHeader: true,
                      headers,
                      models: modelIds.map((modelId) => toProviderModel(modelId)),
                    },
                  },
                },
              },
              defaultModel: `${PROVIDER_ID}/${modelIds[0]}`,
              notes: [
                "Direct upstream connection enabled (no local relay).",
                "API key is sent via Authorization header (authHeader=true).",
              ],
            };
          },
        },
      ],
    });
  },
};

export default plugin;
