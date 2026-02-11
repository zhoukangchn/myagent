# Examples

示例代码展示如何使用 MCP Hub。

## 目录结构

```
examples/
├── weather-server/    # 示例 MCP Server (注册到 Hub)
└── hub-client/        # 示例 Client (从 Hub 发现服务)
```

## 快速开始

### 1. 启动 MCP Hub

```bash
cd ..
uv run python -m mcp_hub.main --port 8000
```

### 2. 启动 Weather Server

```bash
cd weather-server
uv sync
uv run python server.py --port 3001 --hub http://localhost:8000
```

### 3. 运行 Hub Client

```bash
cd hub-client
uv sync
uv run python client.py --hub http://localhost:8000
```

## 预期输出

Hub Client 会显示：
- 已注册的服务列表
- Weather Server 的详细信息
- 调用 get_weather 工具的结果
