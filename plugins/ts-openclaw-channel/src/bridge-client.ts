import crypto from "node:crypto";
import WebSocket from "ws";

export type OutboundMessage = {
  type: string;
  request_id: string;
  session_key?: string;
  seq?: number;
  payload?: Record<string, unknown>;
};

function sha256Hex(input: Buffer | string): string {
  return crypto.createHash("sha256").update(input).digest("hex");
}

function hmacHex(secret: string, payload: string): string {
  return crypto.createHmac("sha256", secret).update(payload).digest("hex");
}

function signHeaders(params: { method: string; path: string; secret: string; openclawId: string }) {
  const timestamp = Math.floor(Date.now() / 1000).toString();
  const nonce = crypto.randomUUID();
  const bodyHash = sha256Hex("");
  const payload = [params.method.toUpperCase(), params.path, timestamp, nonce, bodyHash].join("\n");
  const signature = hmacHex(params.secret, payload);

  return {
    "x-openclaw-id": params.openclawId,
    "x-timestamp": timestamp,
    "x-nonce": nonce,
    "x-signature": signature,
  };
}

export class BridgeClient {
  private ws: WebSocket | null = null;
  private reconnectTimer: NodeJS.Timeout | null = null;
  private shouldReconnect = false;
  private reconnectAttempts = 0;
  private connectParams:
    | { wsUrl: string; secret: string; openclawId: string; onMessage: (msg: unknown) => void; onStatus?: (status: string) => void }
    | null = null;

  connect(params: {
    wsUrl: string;
    secret: string;
    openclawId: string;
    onMessage: (msg: unknown) => void;
    onStatus?: (status: string) => void;
  }) {
    this.connectParams = params;
    this.shouldReconnect = true;
    const url = new URL(params.wsUrl);
    const headers = signHeaders({
      method: "GET",
      path: url.pathname,
      secret: params.secret,
      openclawId: params.openclawId,
    });

    this.ws = new WebSocket(params.wsUrl, { headers });

    this.ws.on("open", () => {
      this.reconnectAttempts = 0;
      params.onStatus?.("open");
      // Keepalive ping for long-lived reverse connection.
      this.ws?.send(JSON.stringify({ type: "ping" }));
    });

    this.ws.on("message", (buf) => {
      try {
        params.onMessage(JSON.parse(buf.toString()));
      } catch {
        params.onMessage({ type: "malformed" });
      }
    });

    this.ws.on("error", () => {
      params.onStatus?.("error");
    });

    this.ws.on("close", () => {
      this.ws = null;
      params.onStatus?.("closed");
      if (!this.shouldReconnect) return;
      this.scheduleReconnect();
    });
  }

  send(msg: OutboundMessage) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;
    this.ws.send(JSON.stringify(msg));
  }

  close() {
    this.shouldReconnect = false;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.ws?.close();
    this.ws = null;
  }

  private scheduleReconnect() {
    if (this.reconnectTimer || !this.connectParams) return;
    const delay = Math.min(30_000, 1_000 * Math.max(1, 2 ** this.reconnectAttempts));
    this.reconnectAttempts += 1;
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      if (!this.shouldReconnect || !this.connectParams) return;
      this.connect(this.connectParams);
    }, delay);
  }
}
