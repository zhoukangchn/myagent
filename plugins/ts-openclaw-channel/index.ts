import type { OpenClawPluginApi } from "openclaw/plugin-sdk";
import { BridgeClient } from "./src/bridge-client.js";

const PLUGIN_ID = "ts-openclaw-channel";

const plugin = {
  id: PLUGIN_ID,
  register(api: OpenClawPluginApi) {
    const wsUrl = process.env.BRIDGE_WS_URL ?? "ws://127.0.0.1:8010/v1/ws/openclaw";
    const secret = process.env.OPENCLAW_SHARED_SECRET ?? "dev-openclaw-secret";
    const openclawId = process.env.OPENCLAW_ID ?? "openclaw-local";

    const client = new BridgeClient();
    client.connect({
      wsUrl,
      secret,
      openclawId,
      onMessage: (_msg) => {
        // TODO: map gateway -> OpenClaw runtime events.
      },
    });

    // TODO: wire OpenClaw runtime output -> client.send(...)
    api.runtime.log?.("info", `[${PLUGIN_ID}] reverse WS client connected to ${wsUrl}`);
  },
};

export default plugin;
