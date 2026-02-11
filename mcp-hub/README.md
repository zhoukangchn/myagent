# MCP Hub

轻量级 MCP 服务注册中心，使用内存存储。

## 架构

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   Client    │ ───▶ │  MCP Hub    │ ◀─── │   Server    │
│  (发现/调用) │      │  (注册中心)  │      │ (自动注册)   │
└─────────────┘      └─────────────┘      └─────────────┘
```

## 快速开始

### 1. 安装依赖

```bash
pip install fastapi uvicorn mcp httpx rich
```

### 2. 启动 Hub

```bash
cd hub
python main.py
```

Hub 运行在 http://localhost:8000

### 3. 启动 Server

```bash
cd server
python main.py --port 3001 --hub http://localhost:8000
```

Server 会自动注册到 Hub，并保持心跳。

### 4. 运行 Client Demo

```bash
cd client
python main.py --hub http://localhost:8000
```

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /register | 注册服务 |
| GET | /services | 列出所有服务 |
| GET | /services/{name} | 获取服务详情 |
| POST | /services/{name}/heartbeat | 服务心跳 |
| DELETE | /services/{name} | 注销服务 |

## 特点

- ✅ 内存存储，无需数据库
- ✅ 自动心跳检测
- ✅ 服务离线自动标记
- ✅ MCP 协议兼容
