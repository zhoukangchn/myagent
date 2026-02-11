#!/usr/bin/env node
import { Server } from '@anthropic-ai/mcp';
import { StdioServerTransport } from '@anthropic-ai/mcp/stdio';
import { SSEServerTransport } from '@anthropic-ai/mcp/sse';
import express from 'express';
import { randomUUID } from 'crypto';
import { readFileSync, readdirSync, statSync } from 'fs';
import { resolve } from 'path';

// ==================== 工具实现 ====================

const calculate = (args: { operation: string; a: number; b: number }) => {
  const { operation, a, b } = args;
  let result: number;
  
  switch (operation) {
    case 'add':
      result = a + b;
      break;
    case 'subtract':
      result = a - b;
      break;
    case 'multiply':
      result = a * b;
      break;
    case 'divide':
      if (b === 0) throw new Error('Cannot divide by zero');
      result = a / b;
      break;
    default:
      throw new Error(`Unknown operation: ${operation}`);
  }
  
  return {
    content: [{ type: 'text', text: `Result: ${result}` }],
  };
};

const getWeather = async (args: { city: string; days?: number }) => {
  const { city, days = 1 } = args;
  
  // 模拟天气数据
  const weathers = ['晴朗', '多云', '小雨', '大雨', '雪', '雾霾'];
  const randomWeather = weathers[Math.floor(Math.random() * weathers.length)];
  const temp = Math.floor(Math.random() * 30) + 5; // 5-35°C
  
  return {
    content: [{
      type: 'text',
      text: `${city}未来${days}天天气: ${randomWeather}, 温度 ${temp}°C`,
    }],
  };
};

const listFiles = (args: { path?: string }) => {
  const targetPath = args.path || '.';
  
  try {
    const entries = readdirSync(targetPath);
    const files = entries.map(name => {
      const fullPath = resolve(targetPath, name);
      const stats = statSync(fullPath);
      return {
        name,
        type: stats.isDirectory() ? 'directory' : 'file',
        size: stats.size,
        modified: stats.mtime.toISOString(),
      };
    });
    
    return {
      content: [{
        type: 'text',
        text: JSON.stringify(files, null, 2),
      }],
    };
  } catch (error: any) {
    return {
      content: [{ type: 'text', text: `Error: ${error.message}` }],
      isError: true,
    };
  }
};

const readFile = (args: { path: string }) => {
  const { path: filePath } = args;
  
  try {
    const content = readFileSync(filePath, 'utf-8');
    return {
      content: [{ type: 'text', text: content }],
    };
  } catch (error: any) {
    return {
      content: [{ type: 'text', text: `Error: ${error.message}` }],
      isError: true,
    };
  }
};

// ==================== 资源实现 ====================

const getSystemInfo = () => {
  return {
    contents: [{
      uri: 'system://info',
      mimeType: 'application/json',
      text: JSON.stringify({
        platform: process.platform,
        arch: process.arch,
        nodeVersion: process.version,
        pid: process.pid,
        uptime: process.uptime(),
        memory: process.memoryUsage(),
      }, null, 2),
    }],
  };
};

const getUserProfile = (uri: string, { id }: { id: string }) => {
  // 模拟用户数据
  const users: Record<string, any> = {
    '1': { name: 'Alice', role: 'admin', email: 'alice@example.com' },
    '2': { name: 'Bob', role: 'user', email: 'bob@example.com' },
  };
  
  const user = users[id] || { name: `User-${id}`, role: 'guest', email: 'unknown' };
  
  return {
    contents: [{
      uri,
      mimeType: 'application/json',
      text: JSON.stringify(user, null, 2),
    }],
  };
};

const getDocs = (uri: string, { topic }: { topic: string }) => {
  const docs: Record<string, string> = {
    'mcp': 'Model Context Protocol (MCP) 是一个开放协议...',
    'tools': 'Tools 允许 LLM 执行操作，如计算、API 调用等...',
    'resources': 'Resources 提供 LLM 可以读取的数据和上下文...',
    'prompts': 'Prompts 是可复用的模板，用于标准化交互...',
  };
  
  const content = docs[topic] || `暂无关于 "${topic}" 的文档`;
  
  return {
    contents: [{
      uri,
      mimeType: 'text/plain',
      text: content,
    }],
  };
};

// ==================== 提示模板 ====================

const codeReviewPrompt = (args: { code: string; language?: string }) => {
  const { code, language = 'unknown' } = args;
  
  return {
    messages: [{
      role: 'user',
      content: {
        type: 'text',
        text: `请审查以下 ${language} 代码，提供改进建议：\n\n\`\`\`${language}\n${code}\n\`\`\`\n\n请从以下方面分析：\n1. 代码质量和可读性\n2. 潜在的错误或漏洞\n3. 性能优化建议\n4. 最佳实践遵循情况`,
      },
    }],
  };
};

const explainConceptPrompt = (args: { concept: string; level?: string }) => {
  const { concept, level = 'intermediate' } = args;
  
  const levelDescriptions: Record<string, string> = {
    'beginner': '用简单易懂的语言解释，适合初学者',
    'intermediate': '提供技术细节和实际例子',
    'advanced': '深入底层原理和实现细节',
  };
  
  return {
    messages: [{
      role: 'user',
      content: {
        type: 'text',
        text: `请解释 "${concept}" 这个概念。\n\n目标受众：${levelDescriptions[level]}`,
      },
    }],
  };
};

// ==================== 服务器初始化 ====================

const server = new Server(
  {
    name: 'mcp-demo-server',
    version: '1.0.0',
  },
  {
    capabilities: {
      tools: {},
      resources: {},
      prompts: {},
    },
  }
);

// 注册工具
server.setRequestHandler('tools/list', async () => ({
  tools: [
    {
      name: 'calculate',
      description: '执行基础数学运算 (add, subtract, multiply, divide)',
      inputSchema: {
        type: 'object',
        properties: {
          operation: {
            type: 'string',
            enum: ['add', 'subtract', 'multiply', 'divide'],
            description: '要执行的数学运算',
          },
          a: { type: 'number', description: '第一个操作数' },
          b: { type: 'number', description: '第二个操作数' },
        },
        required: ['operation', 'a', 'b'],
      },
    },
    {
      name: 'getWeather',
      description: '获取指定城市的天气信息',
      inputSchema: {
        type: 'object',
        properties: {
          city: { type: 'string', description: '城市名称' },
          days: { type: 'number', description: '预报天数 (1-7)', minimum: 1, maximum: 7 },
        },
        required: ['city'],
      },
    },
    {
      name: 'listFiles',
      description: '列出指定路径的文件和目录',
      inputSchema: {
        type: 'object',
        properties: {
          path: { type: 'string', description: '要列出的目录路径 (默认当前目录)' },
        },
      },
    },
    {
      name: 'readFile',
      description: '读取指定文件的内容',
      inputSchema: {
        type: 'object',
        properties: {
          path: { type: 'string', description: '文件路径' },
        },
        required: ['path'],
      },
    },
  ],
}));

server.setRequestHandler('tools/call', async (request) => {
  const { name, arguments: args } = request.params;
  
  switch (name) {
    case 'calculate':
      return calculate(args as any);
    case 'getWeather':
      return getWeather(args as any);
    case 'listFiles':
      return listFiles(args as any);
    case 'readFile':
      return readFile(args as any);
    default:
      throw new Error(`Unknown tool: ${name}`);
  }
});

// 注册资源
server.setRequestHandler('resources/list', async () => ({
  resources: [
    {
      uri: 'system://info',
      name: '系统信息',
      mimeType: 'application/json',
      description: '当前系统的运行信息',
    },
  ],
  resourceTemplates: [
    {
      uriTemplate: 'user://{id}/profile',
      name: '用户资料',
      mimeType: 'application/json',
      description: '获取指定用户的资料信息',
    },
    {
      uriTemplate: 'docs://{topic}',
      name: '文档资源',
      mimeType: 'text/plain',
      description: '获取指定主题的文档',
    },
  ],
}));

server.setRequestHandler('resources/read', async (request) => {
  const { uri } = request.params;
  
  if (uri === 'system://info') {
    return getSystemInfo();
  }
  
  const userMatch = uri.match(/^user:\/\/(.+)\/profile$/);
  if (userMatch) {
    return getUserProfile(uri, { id: userMatch[1] });
  }
  
  const docsMatch = uri.match(/^docs:\/\/(.+)$/);
  if (docsMatch) {
    return getDocs(uri, { topic: docsMatch[1] });
  }
  
  throw new Error(`Unknown resource: ${uri}`);
});

// 注册提示模板
server.setRequestHandler('prompts/list', async () => ({
  prompts: [
    {
      name: 'codeReview',
      description: '代码审查模板',
      arguments: [
        {
          name: 'code',
          description: '要审查的代码',
          required: true,
        },
        {
          name: 'language',
          description: '编程语言',
          required: false,
        },
      ],
    },
    {
      name: 'explainConcept',
      description: '概念解释模板',
      arguments: [
        {
          name: 'concept',
          description: '要解释的概念',
          required: true,
        },
        {
          name: 'level',
          description: '解释深度 (beginner, intermediate, advanced)',
          required: false,
        },
      ],
    },
  ],
}));

server.setRequestHandler('prompts/get', async (request) => {
  const { name, arguments: args } = request.params;
  
  switch (name) {
    case 'codeReview':
      return codeReviewPrompt(args as any);
    case 'explainConcept':
      return explainConceptPrompt(args as any);
    default:
      throw new Error(`Unknown prompt: ${name}`);
  }
});

// ==================== 启动服务器 ====================

const args = process.argv.slice(2);
const useStdio = args.includes('--stdio');
const useSSE = args.includes('--sse');

async function main() {
  if (useStdio) {
    const transport = new StdioServerTransport();
    await server.connect(transport);
    console.error('MCP Server running on stdio');
  } else if (useSSE) {
    const port = parseInt(args[args.indexOf('--port') + 1] || '3001');
    const app = express();
    
    app.get('/sse', async (req, res) => {
      const transport = new SSEServerTransport('/message', res);
      await server.connect(transport);
    });
    
    app.post('/message', async (req, res) => {
      // SSE transport handles this internally
    });
    
    app.listen(port, () => {
      console.error(`MCP Server running on SSE at http://localhost:${port}/sse`);
    });
  } else {
    console.error('Usage: node dist/index.js [--stdio | --sse --port <port>]');
    process.exit(1);
  }
}

main().catch(console.error);
