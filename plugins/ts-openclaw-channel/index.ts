import type { OpenClawPluginApi } from "openclaw/plugin-sdk";
import { BridgeClient } from "./src/bridge-client.js";

const PLUGIN_ID = "ts-openclaw-channel";
const CHANNEL_ID = "sse_bridge";
const DEFAULT_REQUEST_TIMEOUT_MS = 2 * 60 * 1000;

function readPositiveIntEnv(name: string, fallback: number): number {
  const raw = process.env[name]?.trim();
  if (!raw) return fallback;
  const n = Number(raw);
  return Number.isFinite(n) && n > 0 ? Math.floor(n) : fallback;
}

const REQUEST_TIMEOUT_MS = readPositiveIntEnv("BRIDGE_REQUEST_TIMEOUT_MS", DEFAULT_REQUEST_TIMEOUT_MS);
const OPENCLAW_AGENT_TIMEOUT_SEC = readPositiveIntEnv("OPENCLAW_AGENT_TIMEOUT_SEC", 90);

function resolveOpenclawCmd(): string {
  const fromEnv = process.env.OPENCLAW_CMD?.trim();
  if (fromEnv) return fromEnv;
  return process.platform === "win32" ? "openclaw.cmd" : "openclaw";
}

function quoteCmdArg(arg: string): string {
  if (!arg) return '""';
  if (!/[\s"^&|<>]/.test(arg)) return arg;
  return `"${arg.replace(/"/g, '""')}"`;
}

function buildAgentCommand(args: string[]): string[] {
  const cmd = resolveOpenclawCmd();
  if (process.platform !== "win32") return [cmd, ...args];

  const commandLine = [cmd, ...args].map(quoteCmdArg).join(" ");
  return ["cmd.exe", "/d", "/s", "/c", commandLine];
}

type InboundUserMessage = {
  type: "user.message";
  request_id: string;
  session_key?: string;
  payload?: Record<string, unknown>;
};

type InboundSystemEvent = {
  type: "system.event";
  request_id?: string;
  session_key: string;
  payload?: Record<string, unknown>;
};

type AgentCliResult = {
  status?: string;
  result?: {
    payloads?: Array<{ text?: string | null }>;
    meta?: {
      durationMs?: number;
      agentMeta?: {
        usage?: {
          input?: number;
          output?: number;
          total?: number;
        };
      };
    };
  };
};

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  return value as Record<string, unknown>;
}

function asString(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value : null;
}

function toInboundUserMessage(msg: unknown): InboundUserMessage | null {
  const record = asRecord(msg);
  if (!record || record.type !== "user.message") return null;
  const requestId = asString(record.request_id);
  if (!requestId) return null;
  return {
    type: "user.message",
    request_id: requestId,
    session_key: asString(record.session_key) ?? undefined,
    payload: asRecord(record.payload) ?? undefined,
  };
}

function toInboundSystemEvent(msg: unknown): InboundSystemEvent | null {
  const record = asRecord(msg);
  if (!record || record.type !== "system.event") return null;
  const sessionKey = asString(record.session_key);
  if (!sessionKey) return null;
  return {
    type: "system.event",
    request_id: asString(record.request_id) ?? undefined,
    session_key: sessionKey,
    payload: asRecord(record.payload) ?? undefined,
  };
}

function normalizeSessionId(sessionKey: string): string {
  const id = sessionKey.replace(/[^a-zA-Z0-9_-]/g, "_");
  return id.length > 120 ? id.slice(0, 120) : id;
}

function toChatThread(sessionKey: string): { chatId: string; threadId: string } {
  const idx = sessionKey.indexOf(":");
  if (idx <= 0) return { chatId: sessionKey, threadId: "root" };
  return {
    chatId: sessionKey.slice(0, idx),
    threadId: sessionKey.slice(idx + 1) || "root",
  };
}

async function postChannelMessage(params: {
  url: string;
  to: string;
  text: string;
  accountId?: string | null;
}) {
  const { chatId, threadId } = toChatThread(params.to);
  const payload = {
    chat_id: chatId,
    thread_id: threadId,
    message_id: `oc-${Date.now()}`,
    role: "assistant",
    content: params.text,
    metadata: {
      source: "openclaw-cron-delivery",
      account_id: params.accountId ?? "default",
    },
  };

  const resp = await fetch(params.url, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!resp.ok) {
    const detail = await resp.text().catch(() => "");
    throw new Error(`channel post failed: ${resp.status} ${detail.slice(0, 200)}`);
  }
}

function parseJsonFromStdout(stdout: string): AgentCliResult | null {
  const text = stdout.trim();
  if (!text) return null;
  try {
    return JSON.parse(text) as AgentCliResult;
  } catch {
    const start = text.indexOf("{");
    const end = text.lastIndexOf("}");
    if (start < 0 || end <= start) return null;
    try {
      return JSON.parse(text.slice(start, end + 1)) as AgentCliResult;
    } catch {
      return null;
    }
  }
}

function extractReplyText(result: AgentCliResult | null): string {
  const payloads = result?.result?.payloads;
  if (!Array.isArray(payloads)) return "";
  return payloads
    .map((p) => (typeof p?.text === "string" ? p.text : ""))
    .filter(Boolean)
    .join("\n")
    .trim();
}

const plugin = {
  id: PLUGIN_ID,
  register(api: OpenClawPluginApi) {
    const wsUrl = process.env.BRIDGE_WS_URL ?? "ws://127.0.0.1:8010/v1/ws/openclaw";
    const secret = process.env.OPENCLAW_SHARED_SECRET ?? "dev-openclaw-secret";
    const openclawId = process.env.OPENCLAW_ID ?? "openclaw-local";
    const bridgeAgentId = process.env.BRIDGE_OPENCLAW_AGENT_ID ?? "main";
    const bridgeMode = (process.env.BRIDGE_MODE ?? "legacy-cli").trim().toLowerCase();
    const channelPostUrl = process.env.SSE_CHANNEL_POST_URL ?? "";
    const defaultTo = process.env.SSE_CHANNEL_DEFAULT_TO ?? "";

    const client = new BridgeClient();

    api.registerChannel({
      id: CHANNEL_ID,
      meta: {
        id: CHANNEL_ID,
        label: "SSE Bridge",
        selectionLabel: "SSE Bridge",
        docsPath: "/channels/custom/sse-bridge",
        blurb: "Custom channel for OpenClaw cron delivery over HTTP POST",
      },
      capabilities: {
        chatTypes: ["direct"],
        media: false,
      },
      config: {
        listAccountIds: () => ["default"],
        resolveAccount: () => ({ accountId: "default" }),
        defaultAccountId: () => "default",
      },
      outbound: {
        deliveryMode: "direct",
        resolveTarget: ({ to }: { to?: string }) => {
          const target = (typeof to === "string" && to.trim()) ? to.trim() : defaultTo.trim();
          if (!target) return { ok: false, error: new Error("missing target `to` for sse_bridge") };
          return { ok: true, to: target };
        },
        sendText: async (ctx: { to: string; text: string; accountId?: string | null }) => {
          if (!channelPostUrl.trim()) throw new Error("SSE_CHANNEL_POST_URL is empty");
          await postChannelMessage({
            url: channelPostUrl,
            to: ctx.to,
            text: ctx.text,
            accountId: ctx.accountId,
          });
          return {
            channel: CHANNEL_ID,
            messageId: `sse-${Date.now()}`,
            chatId: ctx.to,
          };
        },
        sendMedia: async (ctx: {
          to: string;
          text: string;
          mediaUrl?: string | null;
          accountId?: string | null;
        }) => {
          if (!channelPostUrl.trim()) throw new Error("SSE_CHANNEL_POST_URL is empty");
          const mediaSuffix = ctx.mediaUrl ? `\n${ctx.mediaUrl}` : "";
          await postChannelMessage({
            url: channelPostUrl,
            to: ctx.to,
            text: `${ctx.text ?? ""}${mediaSuffix}`.trim(),
            accountId: ctx.accountId,
          });
          return {
            channel: CHANNEL_ID,
            messageId: `sse-${Date.now()}`,
            chatId: ctx.to,
          };
        },
      },
    });

    const sendError = (requestId: string, sessionKey: string, code: string, message: string) => {
      client.send({
        type: "assistant.error",
        request_id: requestId,
        session_key: sessionKey,
        payload: { code, message },
      });
    };

    client.connect({
      wsUrl,
      secret,
      openclawId,
      onStatus: (status) => {
        api.logger.info?.(`[${PLUGIN_ID}] bridge status=${status}`);
      },
      onMessage: (msg) => {
        const systemEvent = toInboundSystemEvent(msg);
        if (systemEvent) {
          const text = asString(systemEvent.payload?.text) ?? "";
          if (!text) {
            if (systemEvent.request_id) {
              sendError(
                systemEvent.request_id,
                systemEvent.session_key,
                "bad_request",
                "payload.text is required for system.event",
              );
            }
            return;
          }

          const contextKey =
            asString(systemEvent.payload?.context_key) ??
            `bridge:${systemEvent.request_id ?? Date.now().toString()}`;
          const wakeReason = asString(systemEvent.payload?.reason) ?? "bridge:system-event";
          const upstreamSessionKey = `agent:${bridgeAgentId}:${systemEvent.session_key}`;
          const ok = api.runtime.system.enqueueSystemEvent(text, {
            sessionKey: upstreamSessionKey,
            contextKey,
          });
          if (!ok) {
            if (systemEvent.request_id) {
              sendError(
                systemEvent.request_id,
                systemEvent.session_key,
                "enqueue_failed",
                "failed to enqueue system event",
              );
            }
            return;
          }

          api.runtime.system.requestHeartbeatNow({
            sessionKey: upstreamSessionKey,
            reason: wakeReason,
            agentId: bridgeAgentId,
          });

          if (systemEvent.request_id) {
            client.send({
              type: "assistant.done",
              request_id: systemEvent.request_id,
              session_key: systemEvent.session_key,
              payload: {
                accepted: true,
                mode: "heartbeat",
              },
            });
          }
          return;
        }

        const inbound = toInboundUserMessage(msg);
        if (!inbound) return;

        const sessionKey = inbound.session_key ?? inbound.request_id;
        const userText = asString(inbound.payload?.text) ?? "";
        if (!userText) {
          sendError(inbound.request_id, sessionKey, "bad_request", "payload.text is required");
          return;
        }

        const sessionId = normalizeSessionId(`${bridgeAgentId}_${sessionKey}`);

        void (async () => {
          if (bridgeMode !== "legacy-cli") {
            sendError(
              inbound.request_id,
              sessionKey,
              "unsupported_mode",
              `bridge mode '${bridgeMode}' is not implemented in this demo plugin`,
            );
            return;
          }

          const cmd = buildAgentCommand([
            "agent",
            "--agent",
            bridgeAgentId,
            "--session-id",
            sessionId,
            "--message",
            userText,
            "--timeout",
            String(OPENCLAW_AGENT_TIMEOUT_SEC),
            "--json",
          ]);

          api.runtime.log?.(
            "info",
            `[${PLUGIN_ID}] inbound request_id=${inbound.request_id} session_key=${sessionKey} mode=${bridgeMode}`,
          );

          const result = await api.runtime.system.runCommandWithTimeout(cmd, {
            timeoutMs: REQUEST_TIMEOUT_MS,
          });

          api.runtime.log?.(
            "info",
            `[${PLUGIN_ID}] cmd result request_id=${inbound.request_id} code=${result.code} stdout_len=${result.stdout.length} stderr_len=${result.stderr.length}`,
          );

          if (result.code !== 0) {
            const detail = (result.stderr || result.stdout || "openclaw agent failed").trim();
            sendError(inbound.request_id, sessionKey, "upstream_error", detail.slice(0, 800));
            return;
          }

          const parsed = parseJsonFromStdout(result.stdout);
          const replyText = extractReplyText(parsed);
          if (replyText) {
            client.send({
              type: "assistant.delta",
              request_id: inbound.request_id,
              session_key: sessionKey,
              payload: { text: replyText },
            });
          }

          const usage = parsed?.result?.meta?.agentMeta?.usage ?? {};
          const latencyMs = parsed?.result?.meta?.durationMs;
          client.send({
            type: "assistant.done",
            request_id: inbound.request_id,
            session_key: sessionKey,
            payload: { usage, latency_ms: latencyMs },
          });
        })().catch((err: unknown) => {
          sendError(
            inbound.request_id,
            sessionKey,
            "upstream_exception",
            String(err ?? "unknown upstream exception"),
          );
        });
      },
    });

    api.runtime.log?.(
      "info",
      `[${PLUGIN_ID}] reverse WS bridge started: ${wsUrl} mode=${bridgeMode} reqTimeoutMs=${REQUEST_TIMEOUT_MS} agentTimeoutSec=${OPENCLAW_AGENT_TIMEOUT_SEC}`,
    );
  },
};

export default plugin;
