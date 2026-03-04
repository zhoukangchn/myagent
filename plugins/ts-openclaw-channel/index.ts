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

type InboundUserMessage = {
  type: "user.message";
  request_id: string;
  session_key?: string;
  payload?: Record<string, unknown>;
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

const plugin = {
  id: PLUGIN_ID,
  register(api: OpenClawPluginApi) {
    const wsUrl = process.env.BRIDGE_WS_URL ?? "ws://127.0.0.1:8000/v1/ws/openclaw";
    const bridgeAgentId = process.env.BRIDGE_OPENCLAW_AGENT_ID ?? "main";
    const channelPostUrl = process.env.SSE_CHANNEL_POST_URL ?? "http://127.0.0.1:8010/v1/channel/post";
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
      onStatus: (status) => {
        api.logger.info?.(`[${PLUGIN_ID}] bridge status=${status}`);
      },
      onMessage: (msg) => {
        const inbound = toInboundUserMessage(msg);
        if (!inbound) return;

        const sessionKey = inbound.session_key ?? inbound.request_id;
        const userText = asString(inbound.payload?.text) ?? "";
        if (!userText) {
          sendError(inbound.request_id, sessionKey, "bad_request", "payload.text is required");
          return;
        }

        void (async () => {
          api.runtime.log?.(
            "info",
            `[${PLUGIN_ID}] inbound request_id=${inbound.request_id} session_key=${sessionKey}`,
          );

          let delivered = false;
          let lastSentText = "";
          try {
            const route = api.runtime.channel.routing.resolveAgentRoute({
              cfg: api.config,
              channel: CHANNEL_ID,
              accountId: "default",
              peer: { kind: "direct", id: sessionKey },
            });

            const ctxPayload = api.runtime.channel.reply.finalizeInboundContext({
              Body: userText,
              RawBody: userText,
              CommandBody: userText,
              From: `sse_bridge:${asString(inbound.payload?.sender_id) ?? "unknown"}`,
              To: `sse_bridge:${sessionKey}`,
              SessionKey: route.sessionKey,
              AccountId: route.accountId,
              ChatType: "direct",
              ConversationLabel: sessionKey,
              SenderId: asString(inbound.payload?.sender_id) ?? undefined,
              MessageSid: asString(inbound.payload?.message_id) ?? inbound.request_id,
              Timestamp: Date.now(),
              Provider: CHANNEL_ID,
              Surface: CHANNEL_ID,
              OriginatingChannel: CHANNEL_ID,
              OriginatingTo: sessionKey,
              CommandAuthorized: true,
            });

            const dispatchStart = Date.now();
            api.runtime.log?.(
              "info",
              `[${PLUGIN_ID}] dispatch start request_id=${inbound.request_id} session_key=${sessionKey}`,
            );

            await Promise.race([
              api.runtime.channel.reply.dispatchReplyWithBufferedBlockDispatcher({
                ctx: ctxPayload,
                cfg: api.config,
                dispatcherOptions: {
                  deliver: async (payload: { text?: string }, info?: { kind?: string }) => {
                    const text = payload.text ?? "";
                    api.runtime.log?.(
                      "info",
                      `[${PLUGIN_ID}] deliver request_id=${inbound.request_id} kind=${info?.kind ?? "unknown"} text_len=${text.length}`,
                    );
                    if (!text) return;

                    let toSend = "";
                    if (text.startsWith(lastSentText)) {
                      toSend = text.slice(lastSentText.length);
                    } else if (lastSentText.startsWith(text)) {
                      toSend = "";
                    } else {
                      toSend = text;
                    }

                    if (!toSend) return;
                    delivered = true;
                    lastSentText = text;
                    client.send({
                      type: "assistant.delta",
                      request_id: inbound.request_id,
                      session_key: sessionKey,
                      payload: { text: toSend },
                    });
                  },
                  onSkip: (payload: { text?: string }, info: { kind?: string; reason?: string }) => {
                    api.runtime.log?.(
                      "warn",
                      `[${PLUGIN_ID}] skip request_id=${inbound.request_id} kind=${info?.kind ?? "unknown"} reason=${info?.reason ?? "unknown"} text_len=${(payload?.text ?? "").length}`,
                    );
                  },
                  onError: (err: unknown, info: { kind?: string }) => {
                    api.runtime.log?.(
                      "warn",
                      `[${PLUGIN_ID}] dispatcher error request_id=${inbound.request_id} kind=${info?.kind ?? "unknown"} err=${String(err)}`,
                    );
                    throw new Error(`${info.kind}: ${String(err)}`);
                  },
                },
              }),
              new Promise((_, reject) =>
                setTimeout(() => reject(new Error("channel-inbound timeout")), REQUEST_TIMEOUT_MS),
              ),
            ]);

            api.runtime.log?.(
              "info",
              `[${PLUGIN_ID}] dispatch done request_id=${inbound.request_id} elapsed_ms=${Date.now() - dispatchStart} delivered=${delivered}`,
            );
          } catch (err) {
            api.runtime.log?.(
              "warn",
              `[${PLUGIN_ID}] failed request_id=${inbound.request_id}: ${String(err)}`,
            );
            sendError(
              inbound.request_id,
              sessionKey,
              "upstream_error",
              `channel-inbound failed: ${String(err)}`.slice(0, 800),
            );
            return;
          }

          if (!delivered) {
            api.runtime.log?.(
              "warn",
              `[${PLUGIN_ID}] no output request_id=${inbound.request_id}`,
            );
            sendError(
              inbound.request_id,
              sessionKey,
              "upstream_empty",
              "channel-inbound returned no text payload",
            );
            return;
          }

          client.send({
            type: "assistant.done",
            request_id: inbound.request_id,
            session_key: sessionKey,
            payload: {},
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
      `[${PLUGIN_ID}] reverse WS bridge started: ${wsUrl} reqTimeoutMs=${REQUEST_TIMEOUT_MS}`,
    );
  },
};

export default plugin;
