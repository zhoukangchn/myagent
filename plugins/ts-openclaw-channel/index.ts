import type { OpenClawPluginApi } from "openclaw/plugin-sdk";
import { BridgeClient } from "./src/bridge-client.js";

const PLUGIN_ID = "ts-openclaw-channel";
const REQUEST_TIMEOUT_MS = 2 * 60 * 1000;

type InboundUserMessage = {
  type: "user.message";
  request_id: string;
  session_key?: string;
  payload?: Record<string, unknown>;
};

type ActiveTurn = {
  requestId: string;
  sessionKey: string;
  runId?: string;
  done: boolean;
  timeout: NodeJS.Timeout;
};

const DONE_WORDS = new Set([
  "done",
  "complete",
  "completed",
  "finish",
  "finished",
  "stop",
  "stopped",
  "end",
  "ended",
  "success",
  "succeeded",
]);

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  return value as Record<string, unknown>;
}

function asString(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value : null;
}

function collectText(data: Record<string, unknown>): string {
  const keys = ["text", "delta", "content", "chunk", "message"];
  for (const key of keys) {
    const raw = data[key];
    if (typeof raw === "string" && raw) return raw;
  }
  const nested = asRecord(data.payload);
  if (nested) return collectText(nested);
  return "";
}

function lifecycleDone(data: Record<string, unknown>): boolean {
  const keys = ["type", "event", "status", "state", "phase", "action"];
  for (const key of keys) {
    const raw = asString(data[key]);
    if (raw && DONE_WORDS.has(raw.toLowerCase())) return true;
  }
  return false;
}

const plugin = {
  id: PLUGIN_ID,
  register(api: OpenClawPluginApi) {
    const wsUrl = process.env.BRIDGE_WS_URL ?? "ws://127.0.0.1:8010/v1/ws/openclaw";
    const secret = process.env.OPENCLAW_SHARED_SECRET ?? "dev-openclaw-secret";
    const openclawId = process.env.OPENCLAW_ID ?? "openclaw-local";

    const client = new BridgeClient();
    const turnsByRequestId = new Map<string, ActiveTurn>();
    const turnsBySessionKey = new Map<string, ActiveTurn>();

    const clearTurn = (turn: ActiveTurn) => {
      clearTimeout(turn.timeout);
      turnsByRequestId.delete(turn.requestId);
      if (turn.runId) turnsByRequestId.delete(turn.runId);
      if (turnsBySessionKey.get(turn.sessionKey)?.requestId === turn.requestId) {
        turnsBySessionKey.delete(turn.sessionKey);
      }
    };

    const finishTurn = (turn: ActiveTurn, payload: Record<string, unknown>) => {
      if (turn.done) return;
      turn.done = true;
      client.send({
        type: "assistant.done",
        request_id: turn.requestId,
        session_key: turn.sessionKey,
        payload,
      });
      clearTurn(turn);
    };

    const failTurn = (turn: ActiveTurn, code: string, message: string) => {
      if (turn.done) return;
      turn.done = true;
      client.send({
        type: "assistant.error",
        request_id: turn.requestId,
        session_key: turn.sessionKey,
        payload: { code, message },
      });
      clearTurn(turn);
    };

    const bindTurnBySession = (sessionKey: string): ActiveTurn | null => {
      const bySession = turnsBySessionKey.get(sessionKey);
      if (bySession) return bySession;
      return null;
    };

    const toInboundUserMessage = (msg: unknown): InboundUserMessage | null => {
      const record = asRecord(msg);
      if (!record) return null;
      if (record.type !== "user.message") return null;
      const requestId = asString(record.request_id);
      if (!requestId) return null;
      return {
        type: "user.message",
        request_id: requestId,
        session_key: asString(record.session_key) ?? undefined,
        payload: asRecord(record.payload) ?? undefined,
      };
    };

    client.connect({
      wsUrl,
      secret,
      openclawId,
      onStatus: (status) => {
        api.logger.info?.(`[${PLUGIN_ID}] bridge status=${status}`);
      },
      onMessage: (msg) => {
        const inbound = toInboundUserMessage(msg);
        if (!inbound) return;
        const sessionKey = inbound.session_key ?? inbound.request_id;
        const userText = asString(inbound.payload?.text) ?? "";
        if (!userText) {
          client.send({
            type: "assistant.error",
            request_id: inbound.request_id,
            session_key: sessionKey,
            payload: { code: "bad_request", message: "payload.text is required" },
          });
          return;
        }

        const existing = turnsByRequestId.get(inbound.request_id);
        if (existing) clearTurn(existing);

        const turn: ActiveTurn = {
          requestId: inbound.request_id,
          sessionKey,
          done: false,
          timeout: setTimeout(() => {
            failTurn(turn, "upstream_timeout", "OpenClaw turn timed out");
          }, REQUEST_TIMEOUT_MS),
        };
        turnsByRequestId.set(turn.requestId, turn);
        turnsBySessionKey.set(turn.sessionKey, turn);

        const ok = api.runtime.system.enqueueSystemEvent(userText, {
          sessionKey: turn.sessionKey,
          contextKey: turn.requestId,
        });
        if (!ok) {
          failTurn(turn, "enqueue_failed", "failed to enqueue message to OpenClaw");
          return;
        }
        api.runtime.system.requestHeartbeatNow({
          sessionKey: turn.sessionKey,
          reason: `bridge:${turn.requestId}`,
        });
      },
    });

    api.runtime.events.onAgentEvent((evt) => {
      const byRun = turnsByRequestId.get(evt.runId);
      const bySession = evt.sessionKey ? bindTurnBySession(evt.sessionKey) : null;
      const turn = byRun ?? bySession;
      if (!turn || turn.done) return;
      if (!turn.runId) {
        turn.runId = evt.runId;
        turnsByRequestId.set(evt.runId, turn);
      }
      const data = asRecord(evt.data) ?? {};

      if (evt.stream === "assistant") {
        const text = collectText(data);
        if (text) {
          client.send({
            type: "assistant.delta",
            request_id: turn.requestId,
            session_key: turn.sessionKey,
            seq: evt.seq,
            payload: { text },
          });
        }
        if (lifecycleDone(data)) {
          finishTurn(turn, { run_id: evt.runId, seq: evt.seq });
        }
        return;
      }

      if (evt.stream === "tool") {
        client.send({
          type: "tool.event",
          request_id: turn.requestId,
          session_key: turn.sessionKey,
          seq: evt.seq,
          payload: data,
        });
        return;
      }

      if (evt.stream === "error") {
        failTurn(
          turn,
          asString(data.code) ?? "upstream_error",
          asString(data.message) ?? "unknown upstream error",
        );
        return;
      }

      if (evt.stream === "lifecycle" && lifecycleDone(data)) {
        finishTurn(turn, { run_id: evt.runId, seq: evt.seq });
      }
    });

    api.runtime.log?.("info", `[${PLUGIN_ID}] reverse WS bridge started: ${wsUrl}`);
  },
};

export default plugin;
