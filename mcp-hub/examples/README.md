# Examples

MCP Hub 示例代码，包含 Server 和 Client 的完整实现。

## 目录结构

```
examples/
├── weather-server/      # 天气服务示例
├── file-server/         # ⭐ 文件操作服务
├── calc-server/         # ⭐ 数学计算服务
├── time-server/         # ⭐ 时间服务
├── hub-client/          # 基础 Client 示例
└── advanced-client/     # ⭐ 高级 Client 示例
```

## 快速开始

### 1. 启动 MCP Hub

```bash
cd ..
uv sync
uv run python -m mcp_hub.main --port 8000
```

### 2. 启动所有服务 (多个终端)

```bash
# 终端 1: 天气服务
cd weather-server
uv sync
uv run python server.py --port 3001

# 终端 2: 文件服务
cd file-server
uv sync
uv run python server.py --port 3002

# 终端 3: 计算服务
cd calc-server
uv sync
uv run python server.py --port 3003

# 终端 4: 时间服务
cd time-server
uv sync
uv run python server.py --port 3004
```

### 3. 运行 Client 示例

```bash
# 基础 Client
cd hub-client
uv sync
uv run python client.py

# 高级 Client
cd advanced-client
uv sync
uv run python client.py
```

## 服务清单

| 服务名 | 端口 | 功能 |
|--------|------|------|
| weather-server | 3001 | 天气查询 |
| file-server | 3002 | 文件读写、搜索 |
| calc-server | 3003 | 数学计算、单位转换 |
| time-server | 3004 | 时区转换、时间戳 |

## 使用 SDK

### Server SDK

```python
from mcp_hub.sdk import HubServer

app = HubServer(
    name="my-server",
    hub_url="http://localhost:8000",
)

@app.register_tool
async def my_tool(args):
    return "result"

app.run_sync(port=3000)
```

### Client SDK

```python
from mcp_hub.sdk import HubClient

client = HubClient("http://localhost:8000")

# 发现服务
services = await client.discover(tools=["calculate"])

# 调用工具
result = await client.call("calculate", {"a": 1, "b": 2})
```
