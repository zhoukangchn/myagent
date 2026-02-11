# MCP Hub

类似 conserves.so 的 MCP 服务注册中心，提供统一的 MCP Server 注册、发现和服务代理。

## 架构

```
┌─────────────────┐     注册      ┌─────────────────┐     发现      ┌─────────────────┐
│  MCP Server A   │ ─────────────▶│                 │◀─────────────│   MCP Client    │
│  (Weather API)  │               │    MCP Hub      │              │  (Service User) │
└─────────────────┘               │   (Registry)    │              └─────────────────┘
                                  │                 │                    │
┌─────────────────┐     注册      │  - 服务目录      │                    │ 调用
│  MCP Server B   │ ─────────────▶│  - 健康检查      │                    ▼
│  (File System)  │               │  - 路由代理      │              ┌─────────────────┐
└─────────────────┘               │                 │              │  Hub Proxy API  │
                                  └─────────────────┘              │  (可选)         │
                                                                    └─────────────────┘
```

## 快速开始

### 安装

```bash
cd mcp-hub
uv sync
```

### 启动 Hub

```bash
uv run python -m mcp_hub.main --port 8000
```

访问 http://localhost:8000/docs 查看 API 文档。

### 注册服务

```bash
curl -X POST http://localhost:8000/api/v1/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "weather-server",
    "version": "1.0.0",
    "transport": "sse",
    "endpoint": "http://localhost:3001/sse",
    "tools": [
      {"name": "get_weather", "description": "获取天气"}
    ]
  }'
```

### 发现服务

```bash
curl http://localhost:8000/api/v1/services
```

## 目录结构

```
mcp-hub/
├── mcp_hub/           # Hub 核心代码
│   ├── main.py        # FastAPI 入口
│   ├── models/        # 数据模型
│   ├── api/           # API 路由
│   └── services/      # 业务逻辑
├── examples/          # 示例代码
│   ├── weather-server/  # 示例 MCP Server
│   └── hub-client/      # 示例 Client
├── pyproject.toml
└── README.md
```

## API 概览

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/register` | 注册服务 |
| GET | `/api/v1/services` | 列出所有服务 |
| GET | `/api/v1/services/{name}` | 获取服务详情 |
| DELETE | `/api/v1/services/{name}` | 注销服务 |
| POST | `/api/v1/call/{name}/tool` | 代理调用工具 |
| POST | `/api/v1/call/{name}/resource` | 代理读取资源 |

## 示例运行

```bash
# 1. 启动 Hub
cd mcp-hub
uv run python -m mcp_hub.main --port 8000

# 2. 启动示例 Server (另一个终端)
cd mcp-hub/examples/weather-server
uv sync
uv run python server.py --port 3001 --hub http://localhost:8000

# 3. 运行示例 Client (另一个终端)
cd mcp-hub/examples/hub-client
uv sync
uv run python client.py --hub http://localhost:8000
```

## 相关项目

- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [conserves.so](https://conserves.so/) - 类似概念的 API 注册平台
