import WebSocket from "ws";

export type OutboundMessage = {
  type: string;
  request_id: string;
  session_key?: string;
  seq?: number;
  payload?: Record<string, unknown>;
};

export class BridgeClient {
  private ws: WebSocket | null = null;
  private reconnectTimer: NodeJS.Timeout | null = null;
  private shouldReconnect = false;
  private reconnectAttempts = 0;
  private connectParams:
    | { wsUrl: string; onMessage: (msg: unknown) => void; onStatus?: (status: string) => void }
    | null = null;

  connect(params: {
    wsUrl: string;
    onMessage: (msg: unknown) => void;
    onStatus?: (status: string) => void;
  }) {
    this.connectParams = params;
    this.shouldReconnect = true;
    this.ws = new WebSocket(params.wsUrl, {
      headers: {
        "x-openclaw-id": "openclaw-local",
      },
    });

    this.ws.on("open", () => {
      this.reconnectAttempts = 0;
      params.onStatus?.("open");
      // Keepalive ping for long-lived reverse connection.
      this.ws?.send(JSON.stringify({ type: "ping" }));
    });

    this.ws.on("message", (buf) => {
      try {
        const msg = JSON.parse(buf.toString());
        if (msg.type === "ping") {
          this.ws?.send(JSON.stringify({ type: "pong" }));
          return;
        }
        params.onMessage(msg);
      } catch {
        params.onMessage({ type: "malformed" });
      }
    });

    this.ws.on("error", (err) => {
      console.error("[bridge-client] ws error:", err);
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
