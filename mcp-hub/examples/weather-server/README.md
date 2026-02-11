# Weather Server Example

示例 MCP Weather Server，展示如何注册到 MCP Hub。

## 运行

```bash
# 先启动 MCP Hub (在另一个终端)
cd ../../
uv run python -m mcp_hub.main --port 8000

# 启动 Weather Server
cd examples/weather-server
uv sync
uv run python server.py --port 3001 --hub http://localhost:8000
```

## 功能

- 提供天气查询工具
- 自动注册到 MCP Hub
- 支持 SSE 传输
