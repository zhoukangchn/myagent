# Time Server

MCP 时间服务，提供时区转换、时间戳转换等功能。

## 运行

```bash
# 安装依赖
uv sync

# 运行
MCP_HUB_URL=http://localhost:8000 uv run python server.py
```

## 工具列表

| 工具名 | 功能 |
|--------|------|
| `get_time` | 获取当前时间 |
| `list_timezones` | 列出可用时区 |
| `convert_timezone` | 转换时区时间 |
| `get_timestamp` | 获取 Unix 时间戳 |
| `timestamp_to_datetime` | 时间戳转日期时间 |
| `add_time` | 时间加减 |
