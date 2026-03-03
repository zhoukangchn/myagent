declare module "openclaw/plugin-sdk" {
  export type AgentEventPayload = {
    runId: string;
    seq: number;
    stream: string;
    sessionKey?: string;
    data: Record<string, unknown>;
  };

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
          agentId?: string;
          sessionKey?: string;
        }) => void;
      };
      events: {
        onAgentEvent: (listener: (evt: AgentEventPayload) => void) => () => boolean;
      };
    };
    logger: {
      info?: (message: string) => void;
      warn?: (message: string) => void;
      error?: (message: string) => void;
    };
  }
}
