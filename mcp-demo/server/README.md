# MCP Demo Server

一个完整的 MCP Server 示例，支持 stdio 和 SSE 两种传输模式。

## 功能特性

- **Tools**: 计算工具、天气查询、文件操作
- **Resources**: 动态/静态资源、URI 模板支持
- **Prompts**: 提示模板、参数化提示
- **Transports**: stdio 和 Server-Sent Events (SSE)

## 快速开始

```bash
# 安装依赖
npm install

# 编译
npm run build

# 运行 stdio 模式
npm run start:stdio

# 运行 SSE 模式
npm run start:sse

# 使用 MCP Inspector 调试
npm run inspect
```

## 工具列表

| 工具名 | 描述 |
|--------|------|
| `calculate` | 基础数学计算 |
| `getWeather` | 获取城市天气 |
| `listFiles` | 列出目录文件 |
| `readFile` | 读取文件内容 |

## 资源列表

| URI 模板 | 描述 |
|----------|------|
| `system://info` | 系统信息 |
| `user://{id}/profile` | 用户资料 |
| `docs://{topic}` | 文档资源 |

## 提示模板

| 名称 | 描述 |
|------|------|
| `codeReview` | 代码审查模板 |
| `explainConcept` | 概念解释模板 |
