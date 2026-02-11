# MCP Demo Client

MCP Client 示例，演示如何连接 MCP Server 并使用其功能。

## 快速开始

```bash
# 安装依赖
npm install

# 编译
npm run build

# 连接 stdio 模式的 server
npm run start:stdio

# 连接 SSE 模式的 server
npm run start:sse
```

## 功能演示

1. **列出可用工具** - 获取 server 提供的所有 tools
2. **调用工具** - 执行 calculate、getWeather 等工具
3. **读取资源** - 获取 system info、user profile 等资源
4. **获取提示模板** - 使用 prompts 模板生成结构化内容

## 代码结构

```
src/
├── index.ts          # 主入口
├── client.ts         # MCP Client 封装
└── examples.ts       # 使用示例
```
