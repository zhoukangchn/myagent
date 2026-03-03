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

  connect(params: { wsUrl: string; secret: string; openclawId: string; onMessage: (msg: unknown) => void }) {
    const url = new URL(params.wsUrl);
    const headers = signHeaders({
      method: "GET",
      path: url.pathname,
      secret: params.secret,
      openclawId: params.openclawId,
    });

    this.ws = new WebSocket(params.wsUrl, { headers });

    this.ws.on("open", () => {
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

    this.ws.on("close", () => {
      this.ws = null;
    });
  }

  send(msg: OutboundMessage) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;
    this.ws.send(JSON.stringify(msg));
  }
}
