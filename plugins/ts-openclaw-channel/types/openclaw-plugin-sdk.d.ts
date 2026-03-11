declare module "openclaw/plugin-sdk" {
  export interface OpenClawPluginApi {
    config: unknown;
    runtime: {
      log?: (level: string, message: string) => void;
      channel: {
        routing: {
          resolveAgentRoute: (params: {
            cfg: unknown;
            channel: string;
            accountId?: string | null;
            peer?: { kind: string; id: string };
          }) => { agentId: string; accountId: string; sessionKey: string };
        };
        reply: {
          finalizeInboundContext: (ctx: Record<string, unknown>) => Record<string, unknown>;
          dispatchReplyWithBufferedBlockDispatcher: (params: {
            ctx: Record<string, unknown>;
            cfg: unknown;
            dispatcherOptions: Record<string, unknown>;
          }) => Promise<unknown>;
        };
      };
    };
    registerChannel: (registration: unknown) => void;
    logger: {
      info?: (message: string) => void;
      warn?: (message: string) => void;
      error?: (message: string) => void;
    };
  }
}
