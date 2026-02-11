# File Server

MCP 文件操作服务，提供文件读写、搜索等功能。

## 运行

```bash
# 安装依赖
uv sync

# 运行 (自动注册到 Hub)
MCP_HUB_URL=http://localhost:8000 uv run python server.py
```

## 工具列表

| 工具名 | 功能 |
|--------|------|
| `list_files` | 列出目录文件 |
| `read_file` | 读取文件内容 |
| `write_file` | 写入文件内容 |
| `get_file_info` | 获取文件信息 |
| `search_files` | 搜索文件 |
