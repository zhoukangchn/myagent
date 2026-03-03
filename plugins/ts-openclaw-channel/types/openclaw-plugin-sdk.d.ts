declare module "openclaw/plugin-sdk" {
  export interface OpenClawPluginApi {
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
    };
    registerChannel: (registration: unknown) => void;
    logger: {
      info?: (message: string) => void;
      warn?: (message: string) => void;
      error?: (message: string) => void;
    };
  }
}
