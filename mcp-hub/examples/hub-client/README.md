# Hub Client Example

示例 MCP Hub Client，展示如何从 Hub 发现服务并调用。

## 运行

```bash
# 先启动 MCP Hub
cd ../../
uv run python -m mcp_hub.main --port 8000

# 启动 Weather Server (在另一个终端)
cd ../weather-server
uv run python server.py --port 3001 --hub http://localhost:8000

# 运行 Hub Client Demo
cd ../hub-client
uv sync
uv run python client.py --hub http://localhost:8000
```

## 功能

- 列出 Hub 上所有注册的服务
- 查看服务详情和可用工具
- 通过 Hub 代理调用远程服务
