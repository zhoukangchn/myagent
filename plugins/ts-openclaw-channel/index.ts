import {
  createReplyPrefixOptions,
  dispatchReplyFromConfigWithSettledDispatcher,
  type OpenClawPluginApi,
} from "openclaw/plugin-sdk";
import { BridgeClient } from "./src/bridge-client.js";

const PLUGIN_ID = "ts-openclaw-channel";
const CHANNEL_ID = "sse_bridge";
const DEFAULT_REQUEST_TIMEOUT_MS = 2 * 60 * 1000;
const DEFAULT_CHANNEL_POST_TIMEOUT_MS = 5_000;
const DEFAULT_CHANNEL_POST_MAX_ATTEMPTS = 3;

function readPositiveIntEnv(name: string, fallback: number): number {
  const raw = process.env[name]?.trim();
  if (!raw) return fallback;
  const n = Number(raw);
  return Number.isFinite(n) && n > 0 ? Math.floor(n) : fallback;
}

const REQUEST_TIMEOUT_MS = readPositiveIntEnv("BRIDGE_REQUEST_TIMEOUT_MS", DEFAULT_REQUEST_TIMEOUT_MS);
const CHANNEL_POST_TIMEOUT_MS = readPositiveIntEnv(
  "SSE_CHANNEL_POST_TIMEOUT_MS",
  DEFAULT_CHANNEL_POST_TIMEOUT_MS,
);
const CHANNEL_POST_MAX_ATTEMPTS = readPositiveIntEnv(
  "SSE_CHANNEL_POST_MAX_ATTEMPTS",
  DEFAULT_CHANNEL_POST_MAX_ATTEMPTS,
);

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

type InboundUserMessage = {
  type: "user.message";
  request_id: string;
  session_key?: string;
  payload?: Record<string, unknown>;
};

type ActiveSession = {
  requestId: string;
  nextMessageIndex: number;
  liveMessageCount: number;
  lastLiveMessageAt: number;
};

function getSharedActiveSessions(): Map<string, ActiveSession> {
  const globalKey = "__ts_openclaw_channel_active_sessions__";
  const globalState = globalThis as typeof globalThis & {
    [globalKey]?: Map<string, ActiveSession>;
  };
  if (!globalState[globalKey]) {
    globalState[globalKey] = new Map<string, ActiveSession>();
  }
  return globalState[globalKey];
}

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

async function waitForLiveSendSettle(
  activeSessions: Map<string, ActiveSession>,
  sessionKey: string,
  options: { maxWaitMs: number; idleMs: number },
): Promise<void> {
  const start = Date.now();
  for (;;) {
    const active = activeSessions.get(sessionKey);
    if (!active) return;

    const elapsed = Date.now() - start;
    const idleFor = Date.now() - active.lastLiveMessageAt;
    if (active.liveMessageCount > 0 && idleFor >= options.idleMs) return;
    if (elapsed >= options.maxWaitMs) return;

    await sleep(100);
  }
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

  for (let attempt = 1; attempt <= CHANNEL_POST_MAX_ATTEMPTS; attempt += 1) {
    try {
      const resp = await fetch(params.url, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(payload),
        signal: AbortSignal.timeout(CHANNEL_POST_TIMEOUT_MS),
      });
      if (!resp.ok) {
        const detail = await resp.text().catch(() => "");
        throw new Error(`channel post failed: ${resp.status} ${detail.slice(0, 200)}`);
      }
      return;
    } catch (error) {
      const detail = error instanceof Error ? error.message : String(error);
      if (attempt >= CHANNEL_POST_MAX_ATTEMPTS) {
        throw new Error(
          `channel post fetch failed url=${params.url} attempts=${CHANNEL_POST_MAX_ATTEMPTS} cause=${detail}`,
        );
      }
      await sleep(Math.min(1_000, 200 * attempt));
    }
  }
}

const plugin = {
  id: PLUGIN_ID,
  register(api: OpenClawPluginApi) {
    const wsUrl = process.env.BRIDGE_WS_URL ?? "ws://127.0.0.1:8000/v1/ws/openclaw";
    const bridgeAgentId = process.env.BRIDGE_OPENCLAW_AGENT_ID ?? "main";
    const channelPostUrl = process.env.SSE_CHANNEL_POST_URL ?? "http://127.0.0.1:8000/v1/channel/post";
    const defaultTo = process.env.SSE_CHANNEL_DEFAULT_TO ?? "";

    const client = new BridgeClient();
    const activeSessions = getSharedActiveSessions();

    const emitActiveSessionMessage = (sessionKey: string, text: string): boolean => {
      const active = activeSessions.get(sessionKey);
      const trimmed = text.trim();
      if (!active || !trimmed) {
        api.logger.info?.(
          `[${PLUGIN_ID}] live_send_miss session_key=${sessionKey} active=${Boolean(active)} text_len=${trimmed.length}`,
        );
        return false;
      }

      const messageIndex = active.nextMessageIndex;
      active.nextMessageIndex += 1;
      active.liveMessageCount += 1;
      active.lastLiveMessageAt = Date.now();
      api.logger.info?.(
        `[${PLUGIN_ID}] live_send_hit session_key=${sessionKey} request_id=${active.requestId} index=${messageIndex} text_len=${trimmed.length}`,
      );
      client.send({
        type: "assistant.message_start",
        request_id: active.requestId,
        session_key: sessionKey,
        payload: { index: messageIndex },
      });
      client.send({
        type: "assistant.delta",
        request_id: active.requestId,
        session_key: sessionKey,
        payload: { text: trimmed },
      });
      return true;
    };

    api.registerChannel({
      id: CHANNEL_ID,
      meta: {
        id: CHANNEL_ID,
        label: "SSE Bridge",
        selectionLabel: "SSE Bridge",
        docsPath: "/channels/custom/sse-bridge",
        blurb: "Custom channel for OpenClaw cron delivery over HTTP POST",
      },
      messaging: {
        targetResolver: {
          hint: "<chat_id[:thread_id]>",
          // SSE Bridge targets are raw chat/thread session keys, not directory-backed contacts.
          looksLikeId: (raw: string) => Boolean(raw.trim()),
        },
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
          api.logger.info?.(
            `[${PLUGIN_ID}] outbound_send_text to=${ctx.to} text_len=${(ctx.text ?? "").trim().length}`,
          );
          if (emitActiveSessionMessage(ctx.to, ctx.text)) {
            return {
              channel: CHANNEL_ID,
              messageId: `sse-live-${Date.now()}`,
              chatId: ctx.to,
            };
          }
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
          const mediaSuffix = ctx.mediaUrl ? `\n${ctx.mediaUrl}` : "";
          api.logger.info?.(
            `[${PLUGIN_ID}] outbound_send_media to=${ctx.to} text_len=${(`${ctx.text ?? ""}${mediaSuffix}`).trim().length}`,
          );
          if (emitActiveSessionMessage(ctx.to, `${ctx.text ?? ""}${mediaSuffix}`.trim())) {
            return {
              channel: CHANNEL_ID,
              messageId: `sse-live-${Date.now()}`,
              chatId: ctx.to,
            };
          }
          if (!channelPostUrl.trim()) throw new Error("SSE_CHANNEL_POST_URL is empty");
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
          let messageIndex = 0;
          let lastSentText = "";
          let expectBoundaryOnNextDeliver = true;
          let pendingRuntimeBoundaryCount = 0;
          try {
            activeSessions.set(sessionKey, {
              requestId: inbound.request_id,
              nextMessageIndex: 1,
              liveMessageCount: 0,
              lastLiveMessageAt: Date.now(),
            });
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

            const emitAssistantMessageStart = (source: string) => {
              messageIndex += 1;
              lastSentText = "";
              expectBoundaryOnNextDeliver = false;
              pendingRuntimeBoundaryCount = Math.max(0, pendingRuntimeBoundaryCount - 1);
              const active = activeSessions.get(sessionKey);
              if (active) active.nextMessageIndex = messageIndex + 1;
              api.runtime.log?.(
                "info",
                `[${PLUGIN_ID}] message_start request_id=${inbound.request_id} index=${messageIndex} source=${source}`,
              );
              client.send({
                type: "assistant.message_start",
                request_id: inbound.request_id,
                session_key: sessionKey,
                payload: { index: messageIndex },
              });
            };

            const emitDeltaFromSnapshot = (text: string, source: string) => {
              api.runtime.log?.(
                "info",
                `[${PLUGIN_ID}] ${source} request_id=${inbound.request_id} text_len=${text.length}`,
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
            };

            const { onModelSelected, ...prefixOptions } = createReplyPrefixOptions({
              cfg: api.config,
              agentId: route.agentId,
              channel: CHANNEL_ID,
              accountId: route.accountId,
            });

            const { dispatcher, replyOptions, markDispatchIdle, markRunComplete } =
              api.runtime.channel.reply.createReplyDispatcherWithTyping({
                ...prefixOptions,
                humanDelay: api.runtime.channel.reply.resolveHumanDelayConfig(
                  api.config,
                  route.agentId,
                ),
                deliver: async (payload: { text?: string }, info?: { kind?: string }) => {
                  const text = payload.text ?? "";
                  const kind = info?.kind ?? "unknown";
                  if (text && (pendingRuntimeBoundaryCount > 0 || (kind === "final" && expectBoundaryOnNextDeliver))) {
                    emitAssistantMessageStart(`deliver:${kind}`);
                  }
                  emitDeltaFromSnapshot(text, `deliver kind=${info?.kind ?? "unknown"}`);
                  if (text && kind === "final") {
                    expectBoundaryOnNextDeliver = true;
                  }
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
              });

            await Promise.race([
              dispatchReplyFromConfigWithSettledDispatcher({
                cfg: api.config,
                ctxPayload,
                dispatcher,
                onSettled: () => {
                  markDispatchIdle();
                  markRunComplete();
                },
                replyOptions: {
                  ...replyOptions,
                  onModelSelected,
                  onAssistantMessageStart: async () => {
                    pendingRuntimeBoundaryCount += 1;
                    expectBoundaryOnNextDeliver = true;
                    lastSentText = "";
                    api.runtime.log?.(
                      "info",
                      `[${PLUGIN_ID}] message_start pending request_id=${inbound.request_id} count=${pendingRuntimeBoundaryCount}`,
                    );
                  },
                  onToolResult: async (payload: { text?: string; mediaUrls?: string[] }) => {
                    const text = payload.text ?? "";
                    expectBoundaryOnNextDeliver = true;
                    api.runtime.log?.(
                      "info",
                      `[${PLUGIN_ID}] tool_result request_id=${inbound.request_id} text_len=${text.length} media_count=${payload.mediaUrls?.length ?? 0}`,
                    );
                    client.send({
                      type: "tool.event",
                      request_id: inbound.request_id,
                      session_key: sessionKey,
                      payload: {
                        tool: "agent_tool_result",
                        stage: "result",
                        text,
                        media_urls: payload.mediaUrls ?? [],
                      },
                    });
                    if (text.trim()) {
                      emitAssistantMessageStart("tool_result");
                      emitDeltaFromSnapshot(text.trim(), "tool_result");
                      expectBoundaryOnNextDeliver = true;
                    }
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

          const active = activeSessions.get(sessionKey);
          if (active && active.liveMessageCount === 0) {
            await waitForLiveSendSettle(activeSessions, sessionKey, {
              maxWaitMs: 12_000,
              idleMs: 3_500,
            });
          }
          const settledActive = activeSessions.get(sessionKey);
          if (settledActive && settledActive.liveMessageCount > 0) {
            delivered = true;
          }
          activeSessions.delete(sessionKey);
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
          activeSessions.delete(sessionKey);
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
