# AGENTS.md - RAG Agent 项目指南

本文档为 AI 编码助手（Antigravity 等）提供项目规范和操作指引。

## 目录

1. [强制规则](#强制规则)
2. [项目结构](#项目结构)
3. [开发规范](#开发规范)
4. [操作指南](#操作指南)
5. [Agent 架构](#agent-架构)

---

## 强制规则

### 代码变更验证

修改以下内容后，**必须**运行验证流程：

- `app/` 下的任何代码
- `pyproject.toml` 或依赖配置
- 测试文件

**验证命令（按顺序执行）：**

```bash
uv run ruff format .          # 格式化
uv run ruff check . --fix     # lint 并自动修复
uv run python -m pytest       # 运行测试（如有）
```

### 提交前检查

- ✅ 代码已格式化
- ✅ 无 lint 错误
- ✅ 类型注解完整
- ✅ 新功能有对应测试
- ✅ 文档已更新（如涉及 API 变更）
- ✅ 测试代码放置在 `tests/` 目录下（禁止在 `scripts/` 放临时测试脚本）

### 禁止事项

- ❌ 提交 `.env` 文件（含敏感信息）
- ❌ 硬编码 API Key
- ❌ 未经测试的 Agent 流程变更
- ❌ 将测试脚本散落在项目根目录或 `scripts/`（必须进 `tests/` 并遵循 pytest 规范）

---

## 项目结构

```
rag-test/
├── src/
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── graph.py         # Agent 流程构建
│   │   ├── nodes.py         # 节点逻辑 (check, retrieve, generate...)
│   │   └── state.py         # 状态定义
│   ├── api/
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── chat.py      # 聊天接口
│   │   │   └── health.py    # 健康检查
│   │   ├── __init__.py
│   │   ├── app.py           # FastAPI App 工厂
│   │   └── schemas.py       # Pydantic 模型
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py        # 配置管理
│   │   └── logging.py       # 日志配置
│   ├── services/
│   │   ├── __init__.py
│   │   ├── knowledge.py     # 知识检索服务
│   │   └── llm.py           # LLM 服务
│   └── __init__.py
├── tests/               # 测试目录
├── .env                 # 环境变量（不提交）
├── .env.example         # 环境变量模板
├── pyproject.toml       # 项目配置
├── Makefile             # 常用命令快捷方式
├── AGENTS.md            # 本文件
└── README.md            # 项目说明
```

### 关键文件说明

| 文件 | 职责 | 修改注意事项 |
|------|------|--------------|
| `src/agents/graph.py` | Agent 流程图 | 修改后必须测试 `/chat/stream` |
| `src/agents/nodes.py` | 节点逻辑 | 核心业务逻辑所在 |
| `src/services/knowledge.py` | 知识检索 | 接口变更需同步更新 nodes.py |
| `src/api/app.py` | API 入口 | FastAPI 应用配置 |
| `src/core/config.py` | 配置管理 | 新增配置需同步 .env.example |

---

## 开发规范

### 技术栈

- **Python**: 3.11+
- **包管理**: uv
- **框架**: FastAPI + LangGraph
- **LLM**: DeepSeek (通过 langchain-openai)
- **知识检索**: Tavily API
- **格式化/Lint**: ruff

### 代码风格

```python
# ✅ 正确示例
async def search_knowledge(query: str) -> list[dict]:
    """
    使用 Tavily 搜索相关内容。
    
    Args:
        query: 搜索查询词
        
    Returns:
        检索结果列表，每项包含 content, source, score
    """
    ...

# ❌ 错误示例
def search(q):  # 缺少类型注解和文档
    ...
```

### 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 函数/变量 | snake_case | `search_knowledge`, `need_knowledge` |
| 类 | PascalCase | `AgentState`, `ChatRequest` |
| 常量 | UPPER_SNAKE_CASE | `MAX_ITERATIONS`, `DEEPSEEK_MODEL` |

### 导入顺序

```python
# 1. 标准库
import sys
from pathlib import Path

# 2. 第三方库
from fastapi import FastAPI
from langchain_openai import ChatOpenAI

# 3. 本地模块
from src.core.config import settings
from src.services.knowledge import search_knowledge
```

### 注释语言

- 代码注释：**中文**
- Docstring：**中文**
- Git commit：**英文**（遵循 conventional commits）

---

## 操作指南

### 环境设置

```bash
# 克隆并进入项目
cd ~/rag-test

# 安装依赖
make install
# 或者: uv sync

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入 API Key
```

### 开发服务器

```bash
# 启动开发服务器（热重载）
make dev
# 或者: uv run python -m src.api.app

# 访问 API 文档
open http://localhost:8000/docs
```

### 测试流式输出

```bash
curl -N -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "2024年诺贝尔物理学奖是谁"}'
```

### 常用命令 (Makefile)

| 命令 | 说明 |
|------|------|
| `make install` | 安装依赖 |
| `make dev` | 启动开发服务器 |
| `make format` | 格式化代码 (ruff) |
| `make lint` | 检查代码规范 |
| `make test` | 运行测试 |
| `make all` | 运行所有检查 (fmt+lint+test) |

### Git 工作流

```bash
# 1. 创建功能分支
git checkout -b feat/xxx

# 2. 开发并验证
make all

# 3. 提交（使用 conventional commits）
git commit -m "feat: add xxx feature"
git commit -m "fix: resolve xxx issue"
git commit -m "docs: update xxx documentation"

# 4. 推送
git push origin feat/xxx
```

---

## Agent 架构

### 流程图

```
START
  │
  ▼
┌─────────┐
│  check  │ ← 判断是否需要检索
└────┬────┘
     │
     ▼ (need_knowledge?)
    ╱ ╲
   ╱   ╲
  YES   NO
   │     │
   ▼     │
┌──────────┐   │
│ retrieve │   │
└────┬─────┘   │
     │         │
     ▼         ▼
┌──────────────────┐
│     generate     │ ← 生成回答
└────────┬─────────┘
         │
         ▼
┌─────────────────┐
│     reflect     │ ← 自我评估
└────────┬────────┘
         │
         ▼ (is_satisfied?)
        ╱ ╲
       ╱   ╲
     YES    NO ──→ 返回 check（最多 3 轮）
      │
      ▼
┌──────────┐
│ finalize │
└────┬─────┘
     │
     ▼
    END
```

### 状态定义

```python
class AgentState(TypedDict):
    messages: list              # 对话历史
    knowledge_context: str      # 检索到的知识
    need_knowledge: bool        # 是否需要检索
    current_answer: str         # 当前生成的回答
    reflection: str             # 反思意见
    is_satisfied: bool          # 是否满意当前回答
    iteration: int              # 当前迭代轮次（最大 3）
```

### 节点说明

| 节点 | 职责 | 输入 | 输出 |
|------|------|------|------|
| check | 判断是否需要外部知识 | messages | need_knowledge |
| retrieve | 调用 Tavily 搜索 | messages, reflection | knowledge_context |
| generate | 用 DeepSeek 生成回答 | messages, knowledge_context | current_answer |
| reflect | 评估回答质量 | current_answer, knowledge_context | is_satisfied, reflection |
| finalize | 输出最终回答 | current_answer | messages |

### 扩展指南

#### 添加新节点

1. 在 `agent.py` 定义异步函数：
   ```python
   async def my_node(state: AgentState) -> AgentState:
       # 处理逻辑
       return {**state, "new_field": value}
   ```

2. 注册节点：
   ```python
   graph.add_node("my_node", my_node)
   ```

3. 连接边：
   ```python
   graph.add_edge("previous_node", "my_node")
   ```

#### 添加新工具

1. 在 `app/` 下创建模块（如 `app/tools/wikipedia.py`）
2. 在 `agent.py` 导入并在相应节点中调用
3. 更新 `.env.example` 如需新配置

---

## API 接口

| 端点 | 方法 | 说明 | 响应类型 |
|------|------|------|----------|
| `/` | GET | 健康检查 | JSON |
| `/health` | GET | 健康检查 | JSON |
| `/chat` | POST | 聊天（非流式） | JSON |
| `/chat/stream` | POST | 聊天（流式） | SSE |

### 请求示例

```json
{
  "message": "2024年诺贝尔物理学奖是谁获得的"
}
```

### 响应示例（非流式）

```json
{
  "reply": "2024年诺贝尔物理学奖...",
  "used_knowledge": true,
  "iterations": 1
}
```

### 响应示例（流式 SSE）

```
data: {"step": "check", "detail": "需要检索知识: 是"}
data: {"step": "retrieve", "detail": "检索到 1500 字符的知识"}
data: {"step": "generate", "detail": "生成回答 (第 1 轮)", "answer": "..."}
data: {"step": "reflect", "detail": "反思评估: 满意"}
data: {"step": "finalize", "detail": "完成"}
data: {"step": "done"}
```

---

## 注意事项

- `MAX_ITERATIONS = 3` 防止反思死循环，可按需调整
- 修改 Agent 流程后务必测试 `/chat/stream` 确认步骤正确
- 保持 stream/non-stream 两个接口行为一致
- 新增环境变量时同步更新 `.env.example`
