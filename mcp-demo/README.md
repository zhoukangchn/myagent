# MCP Demo (Python)

一个完整的 Model Context Protocol (MCP) 示例项目，使用 Python 实现 Server 和 Client。

## 项目结构

```
mcp-demo/
├── server/          # MCP Server 实现
│   ├── server.py    # Server 主入口
│   ├── requirements.txt
│   └── README.md
├── client/          # MCP Client 实现
│   ├── client.py    # Client 主入口
│   ├── requirements.txt
│   └── README.md
└── README.md        # 本文件
```

## 快速开始

### 1. 安装依赖

```bash
# Server
cd server
pip install -r requirements.txt

# Client
cd ../client
pip install -r requirements.txt
```

### 2. 运行 Server (stdio 模式)

```bash
cd server
python server.py --stdio
```

### 3. 运行 Client (stdio 模式)

```bash
cd client
python client.py --transport stdio
```

## 传输模式

### stdio 模式

适合本地进程间通信：

```bash
# Server
python server.py --stdio

# Client (另一个终端)
python client.py --transport stdio
```

### SSE 模式

适合网络通信：

```bash
# 启动 Server (端口 3001)
python server.py --sse --port 3001

# 另一个终端启动 Client
python client.py --transport sse --url http://localhost:3001/sse
```

## 功能特性

### Server 提供的 Tools

| 工具名 | 功能 |
|--------|------|
| `calculate` | 数学运算 (加减乘除) |
| `get_weather` | 模拟天气查询 |
| `list_files` | 列出目录文件 |
| `read_file` | 读取文件内容 |

### Server 提供的 Resources

| URI | 描述 |
|-----|------|
| `system://info` | 系统运行信息 |
| `user://{id}/profile` | 用户资料 (模板) |
| `docs://{topic}` | 文档资源 (模板) |

### Server 提供的 Prompts

| 名称 | 用途 |
|------|------|
| `code_review` | 代码审查模板 |
| `explain_concept` | 概念解释模板 |

## 相关链接

- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [MCP 官方文档](https://modelcontextprotocol.io/)
