# RAG Agent

> Agentic RAG with LangGraph + DeepSeek + Self-Reflection

一个带有自我反思能力的 RAG Agent 脚手架项目。

## ✨ 特性

- 🧠 **自我反思** - Agent 会评估自己的回答质量，不满意时自动重新检索和生成
- 🔍 **智能检索** - 自动判断是否需要外部知识，按需调用 Tavily 搜索
- 📡 **流式输出** - SSE 实时显示每个处理步骤
- 🚀 **生产就绪** - 完整的 CI/CD、Docker、测试配置

## 🏗️ 架构

```
请求 → 判断是否需要知识 → 检索 → 生成回答 → 反思评估 → 返回
                                              ↓
                                    [不满意] 重新检索（最多3轮）
```

## 📁 项目结构

```
rag-test/
├── src/
│   ├── api/                    # FastAPI 层
│   │   ├── app.py              # 应用入口
│   │   ├── schemas.py          # 请求/响应模型
│   │   └── routes/             # 路由
│   │       ├── chat.py         # 聊天接口
│   │       └── health.py       # 健康检查
│   ├── agents/                 # LangGraph Agent 层
│   │   ├── graph.py            # Graph 构建
│   │   ├── nodes.py            # 节点定义
│   │   └── state.py            # 状态定义
│   ├── services/               # 外部服务
│   │   ├── knowledge.py        # Tavily 知识检索
│   │   └── llm.py              # LLM 服务
│   └── core/                   # 核心模块
│       ├── config.py           # 配置管理
│       └── logging.py          # 日志
├── tests/                      # 测试
├── .github/workflows/          # CI/CD
├── Makefile                    # 常用命令
├── Dockerfile                  # Docker 构建
└── docker-compose.yml          # Docker Compose
```

## 🚀 快速开始

### 环境要求

- Python 3.11+
- [uv](https://github.com/astral-sh/uv)

### 安装

```bash
# 克隆项目
git clone https://github.com/zhoukangchn/rag-test.git
cd rag-test

# 安装依赖
make install

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入 API Key
```

### 运行

```bash
# 开发模式
make dev

# 或使用 Docker
docker compose up
```

访问 http://localhost:8000/docs 查看 API 文档。

## 📖 API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/chat` | POST | 聊天（非流式） |
| `/chat/stream` | POST | 聊天（流式 SSE） |
| `/health` | GET | 健康检查 |

### 示例请求

```bash
# 非流式
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "2024年诺贝尔物理学奖是谁获得的"}'

# 流式
curl -N -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "2024年诺贝尔物理学奖是谁获得的"}'
```

## 🛠️ 开发

```bash
make help          # 查看所有命令
make format        # 格式化代码
make lint          # 检查代码规范
make test          # 运行测试
make test-cov      # 测试 + 覆盖率
make all           # 运行所有检查
```

### Pre-commit Hooks

```bash
# 安装 pre-commit hooks
uv run pre-commit install
```

## 🔧 配置

| 环境变量 | 说明 | 必填 |
|----------|------|------|
| `DEEPSEEK_API_KEY` | DeepSeek API Key | ✅ |
| `TAVILY_API_KEY` | Tavily API Key | ✅ |
| `DEEPSEEK_MODEL` | 模型名称 | ❌ (默认: deepseek-chat) |
| `MAX_ITERATIONS` | 最大反思轮次 | ❌ (默认: 3) |

## 📄 License

MIT
