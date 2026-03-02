import type {
  OpenClawPluginApi,
  ProviderAuthContext,
  ProviderAuthResult,
} from "openclaw/plugin-sdk";

const PLUGIN_ID = "internal-model-provider";
const PROVIDER_ID = "internal-model";
const PROVIDER_LABEL = "Internal Model";
const DEFAULT_BASE_URL = "https://your-gateway.example.com/v1";
const DEFAULT_MODEL_IDS = "gpt-4o-mini";

function normalizeBaseUrl(raw: string): string {
  const trimmed = raw.trim();
  if (!trimmed) {
    throw new Error("Upstream base URL is required");
  }
  const withProtocol = trimmed.startsWith("http") ? trimmed : `https://${trimmed}`;
  return withProtocol.endsWith("/v1") ? withProtocol : `${withProtocol.replace(/\/+$/, "")}/v1`;
}

function parseCustomHeaders(raw: string | undefined): Record<string, string> {
  if (!raw || !raw.trim()) {
    return {};
  }
  try {
    const parsed = JSON.parse(raw);
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
  } catch (e) {
    throw new Error(`Invalid custom headers JSON: ${e instanceof Error ? e.message : "unknown error"}`);
  }
}

function buildModelList(modelIds: string[]): Array<{
  id: string;
  name: string;
  contextWindow: number;
  maxTokens: number;
}> {
  return modelIds.map((id) => ({
    id: id.trim(),
    name: id.trim(),
    contextWindow: 128000,
    maxTokens: 8192,
  }));
}

const plugin = {
  id: PLUGIN_ID,
  register(api: OpenClawPluginApi) {
    api.registerProvider({
      id: PROVIDER_ID,
      label: PROVIDER_LABEL,
      auth: [
        {
          id: "api-key",
          label: "API Key",
          hint: "Configure internal model gateway with API key and custom headers",
          run: async (ctx: ProviderAuthContext): Promise<ProviderAuthResult> => {
            const baseUrl = await ctx.prompter.text({
              message: "Upstream base URL",
              initialValue: DEFAULT_BASE_URL,
              validate: (value) => {
                if (!value?.trim()) return "URL is required";
                return undefined;
              },
            });

            const apiKey = await ctx.prompter.text({
              message: "API key (Bearer token)",
              validate: (value) => {
                return value?.trim()?.length > 0 ? undefined : "API key is required";
              },
            });

            const headersInput = await ctx.prompter.text({
              message: "Custom headers JSON (optional, e.g. {\"x-tenant-id\":\"team-a\"})",
              initialValue: "{}",
            });

            const modelIdsInput = await ctx.prompter.text({
              message: "Model IDs (comma-separated)",
              initialValue: DEFAULT_MODEL_IDS,
              validate: (value) => {
                return value?.trim()?.length > 0 ? undefined : "At least one model ID is required";
              },
            });

            const normalizedUrl = normalizeBaseUrl(baseUrl);
            const customHeaders = parseCustomHeaders(headersInput);
            const modelIds = modelIdsInput.split(",").map((s) => s.trim()).filter(Boolean);
            const models = buildModelList(modelIds);

            return {
              profiles: [
                {
                  profileId: `${PROVIDER_ID}:default`,
                  credential: {
                    type: "api_key",
                    provider: PROVIDER_ID,
                    key: apiKey.trim(),
                  },
                },
              ],
              configPatch: {
                models: {
                  providers: {
                    [PROVIDER_ID]: {
                      baseUrl: normalizedUrl,
                      apiKey: apiKey.trim(),
                      api: "openai-completions",
                      authHeader: true,
                      headers: customHeaders,
                      models,
                    },
                  },
                },
              },
              notes: [
                `Provider endpoint: ${normalizedUrl}`,
                `Models: ${modelIds.join(", ")}`,
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
