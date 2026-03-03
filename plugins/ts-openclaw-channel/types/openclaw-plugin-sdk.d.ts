declare module "openclaw/plugin-sdk" {
  export interface OpenClawPluginApi {
    runtime: {
      log?: (level: string, message: string) => void;
    };
  }
}
