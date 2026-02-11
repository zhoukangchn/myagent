# MCP Demo

一个完整的 Model Context Protocol (MCP) 示例项目，包含 Server 和 Client 的实现。

## 项目结构

```
mcp-demo/
├── server/          # MCP Server 实现
│   ├── src/
│   │   └── index.ts    # Server 主入口
│   ├── package.json
│   └── tsconfig.json
├── client/          # MCP Client 实现
│   ├── src/
│   │   ├── client.ts   # Client 封装类
│   │   ├── examples.ts # 使用示例
│   │   └── index.ts    # Client 主入口
│   ├── package.json
│   └── tsconfig.json
└── README.md
```

## 快速开始

### 1. 安装依赖

```bash
cd server && npm install
cd ../client && npm install
```

### 2. 编译

```bash
cd server && npm run build
cd ../client && npm run build
```

### 3. 运行 Server (stdio 模式)

```bash
cd server
npm run start:stdio
```

### 4. 运行 Client (stdio 模式)

```bash
cd client
npm run start:stdio
```

## 传输模式

### stdio 模式

适合本地进程间通信，Client 直接启动 Server 进程：

```bash
# Server
npm run start:stdio

# Client
npm run start:stdio
```

### SSE 模式

适合网络通信，Server 作为独立服务运行：

```bash
# 启动 Server (端口 3001)
cd server
npm run start:sse

# 另一个终端启动 Client
cd client
npm run start:sse
```

## 功能特性

### Server 提供的 Tools

| 工具名 | 功能 |
|--------|------|
| `calculate` | 数学运算 (加减乘除) |
| `getWeather` | 模拟天气查询 |
| `listFiles` | 列出目录文件 |
| `readFile` | 读取文件内容 |

### Server 提供的 Resources

| URI | 描述 |
|-----|------|
| `system://info` | 系统运行信息 |
| `user://{id}/profile` | 用户资料 (模板) |
| `docs://{topic}` | 文档资源 (模板) |

### Server 提供的 Prompts

| 名称 | 用途 |
|------|------|
| `codeReview` | 代码审查模板 |
| `explainConcept` | 概念解释模板 |

## 调试

使用 MCP Inspector 调试 Server：

```bash
cd server
npm run inspect
```

## 相关链接

- [MCP 官方文档](https://modelcontextprotocol.io/)
- [MCP TypeScript SDK](https://github.com/anthropics/mcp-typescript-sdk)
