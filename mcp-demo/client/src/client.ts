import { Client } from '@anthropic-ai/mcp';
import { StdioClientTransport } from '@anthropic-ai/mcp/stdio';
import { SSEClientTransport } from '@anthropic-ai/mcp/sse';
import { spawn } from 'child_process';

export interface ClientConfig {
  transport: 'stdio' | 'sse';
  command?: string;
  args?: string[];
  url?: string;
}

export class MCPDemoClient {
  private client: Client;
  private transport: StdioClientTransport | SSEClientTransport | null = null;

  constructor() {
    this.client = new Client(
      {
        name: 'mcp-demo-client',
        version: '1.0.0',
      },
      {
        capabilities: {},
      }
    );
  }

  async connect(config: ClientConfig): Promise<void> {
    if (config.transport === 'stdio') {
      if (!config.command) {
        throw new Error('stdio transport requires command');
      }
      
      this.transport = new StdioClientTransport({
        command: config.command,
        args: config.args || [],
      });
    } else if (config.transport === 'sse') {
      if (!config.url) {
        throw new Error('sse transport requires url');
      }
      
      this.transport = new SSEClientTransport(new URL(config.url));
    } else {
      throw new Error(`Unknown transport: ${config.transport}`);
    }

    await this.client.connect(this.transport);
    console.log('✅ Connected to MCP Server');
  }

  async disconnect(): Promise<void> {
    await this.client.close();
    console.log('👋 Disconnected from MCP Server');
  }

  // ===== Tools =====
  
  async listTools() {
    const response = await this.client.listTools();
    return response.tools;
  }

  async callTool(name: string, args: Record<string, any>) {
    const response = await this.client.callTool({
      name,
      arguments: args,
    });
    return response;
  }

  // ===== Resources =====

  async listResources() {
    const response = await this.client.listResources();
    return {
      resources: response.resources,
      templates: response.resourceTemplates,
    };
  }

  async readResource(uri: string) {
    const response = await this.client.readResource({ uri });
    return response.contents;
  }

  // ===== Prompts =====

  async listPrompts() {
    const response = await this.client.listPrompts();
    return response.prompts;
  }

  async getPrompt(name: string, args?: Record<string, string>) {
    const response = await this.client.getPrompt({
      name,
      arguments: args,
    });
    return response.messages;
  }
}
