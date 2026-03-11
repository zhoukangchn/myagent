declare module "openclaw/plugin-sdk" {
  type HumanDelayConfig =
    | { mode: "off" }
    | { mode: "natural" }
    | { mode: "custom"; minMs?: number; maxMs?: number };

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
            dispatcherOptions: {
              deliver: (payload: { text?: string }, info?: { kind?: string }) => Promise<void>;
              onSkip?: (payload: { text?: string }, info: { kind?: string; reason?: string }) => void;
              onError?: (err: unknown, info: { kind?: string }) => void;
              onReplyStart?: () => Promise<void> | void;
              humanDelay?: HumanDelayConfig;
            };
            replyOptions?: {
              onAssistantMessageStart?: () => Promise<void> | void;
            };
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
