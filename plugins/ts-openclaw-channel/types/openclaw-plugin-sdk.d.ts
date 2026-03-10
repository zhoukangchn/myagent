declare module "openclaw/plugin-sdk" {
  export function createReplyPrefixOptions(params: {
    cfg: unknown;
    agentId?: string;
    channel: string;
    accountId?: string;
  }): { onModelSelected?: (...args: unknown[]) => void; [key: string]: unknown };
  export function dispatchReplyFromConfigWithSettledDispatcher(params: {
    cfg: unknown;
    ctxPayload: Record<string, unknown>;
    dispatcher: unknown;
    onSettled: () => void | Promise<void>;
    replyOptions?: Record<string, unknown>;
  }): Promise<{ counts: Record<string, number>; queuedFinal?: boolean }>;

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
          createReplyDispatcherWithTyping: (params: {
            deliver: (payload: { text?: string }, info?: { kind?: string }) => Promise<void>;
            responsePrefix?: string;
            responsePrefixContext?: Record<string, unknown>;
            responsePrefixContextProvider?: () => Record<string, unknown>;
            onHeartbeatStrip?: () => void;
            onIdle?: () => void;
            onError?: (err: unknown, info: { kind?: string }) => void;
            onSkip?: (
              payload: { text?: string },
              info: { kind?: string; reason?: string },
            ) => void;
            humanDelay?: unknown;
            typingCallbacks?: unknown;
            onReplyStart?: () => Promise<void> | void;
            onCleanup?: () => void;
          }) => {
            dispatcher: unknown;
            replyOptions: Record<string, unknown>;
            markDispatchIdle: () => void;
            markRunComplete: () => void;
          };
          resolveHumanDelayConfig: (cfg: unknown, agentId: string) => unknown;
          dispatchReplyFromConfig: (params: {
            ctx: Record<string, unknown>;
            cfg: unknown;
            dispatcher: unknown;
            replyOptions?: Record<string, unknown>;
          }) => Promise<unknown>;
          withReplyDispatcher: (params: {
            dispatcher: unknown;
            run: () => Promise<unknown>;
            onSettled?: () => void | Promise<void>;
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
