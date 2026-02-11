#!/usr/bin/env node
import { MCPDemoClient } from './client.js';
import { runExamples } from './examples.js';

function parseArgs() {
  const args = process.argv.slice(2);
  const config: {
    transport: 'stdio' | 'sse';
    url?: string;
    serverPath?: string;
  } = {
    transport: 'stdio',
  };

  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--transport':
        config.transport = args[++i] as 'stdio' | 'sse';
        break;
      case '--url':
        config.url = args[++i];
        break;
      case '--server-path':
        config.serverPath = args[++i];
        break;
    }
  }

  return config;
}

async function main() {
  const config = parseArgs();
  const client = new MCPDemoClient();

  try {
    if (config.transport === 'stdio') {
      // 默认使用相对路径启动 server
      const serverPath = config.serverPath || '../server/dist/index.js';
      console.log('🔗 通过 stdio 连接 MCP Server...');
      await client.connect({
        transport: 'stdio',
        command: 'node',
        args: [serverPath, '--stdio'],
      });
    } else {
      const url = config.url || 'http://localhost:3001/sse';
      console.log(`🔗 通过 SSE 连接 MCP Server (${url})...`);
      await client.connect({
        transport: 'sse',
        url,
      });
    }

    // 运行示例
    await runExamples(client);

  } catch (error) {
    console.error('❌ Error:', error);
    process.exit(1);
  } finally {
    await client.disconnect();
  }
}

main();
