# MCP Demo Client (Python)

MCP Client 示例，演示如何连接 MCP Server 并使用其功能。

## 快速开始

```bash
# 使用 uv 安装依赖并创建虚拟环境
uv sync

# 连接 stdio 模式的 server
uv run python client.py --transport stdio

# 连接 SSE 模式的 server
uv run python client.py --transport sse --url http://localhost:3001/sse
```

## 功能演示

1. **列出可用工具** - 获取 server 提供的所有 tools
2. **调用工具** - 执行 calculate、get_weather 等工具
3. **读取资源** - 获取 system info、user profile 等资源
4. **获取提示模板** - 使用 prompts 模板生成结构化内容
