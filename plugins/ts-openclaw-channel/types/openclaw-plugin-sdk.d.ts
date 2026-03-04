declare module "openclaw/plugin-sdk" {
  export function createNormalizedOutboundDeliverer(
    deliver: (payload: { text?: string; replyToId?: string | null }) => Promise<void>,
  ): (payload: { text?: string; replyToId?: string | null }) => Promise<void>;

  export function createReplyPrefixOptions(params: {
    cfg: unknown;
    agentId?: string;
    channel: string;
    accountId?: string;
  }): { onModelSelected?: (...args: unknown[]) => void; [key: string]: unknown };

  export interface OpenClawPluginApi {
    config: unknown;
    runtime: {
      log?: (level: string, message: string) => void;
      system: {
        enqueueSystemEvent: (
          text: string,
          options: { sessionKey: string; contextKey?: string | null },
        ) => boolean;
        requestHeartbeatNow: (options?: {
          reason?: string;
          coalesceMs?: number;
          agentId?: string;
          sessionKey?: string;
        }) => void;
        runCommandWithTimeout: (
          argv: string[],
          options: { timeoutMs: number; cwd?: string; input?: string; env?: Record<string, string> },
        ) => Promise<{
          pid?: number;
          stdout: string;
          stderr: string;
          code: number | null;
          signal: string | null;
          killed: boolean;
          termination: "exit" | "timeout" | "no-output-timeout" | "signal";
          noOutputTimedOut?: boolean;
        }>;
      };
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
            replyOptions?: Record<string, unknown>;
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
