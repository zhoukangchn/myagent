# AGENTS.md - RAG Agent 项目指南

## 项目概述

这是一个 Agentic RAG 项目，使用 LangGraph + FastAPI + DeepSeek，带有自我反思能力。

## 技术栈

- **Python**: 3.11+
- **包管理**: uv
- **框架**: FastAPI + LangGraph
- **LLM**: DeepSeek (通过 langchain-openai)
- **知识检索**: Tavily API

## 目录结构

```
rag-test/
├── app/
│   ├── __init__.py
│   ├── config.py      # 配置管理（环境变量）
│   ├── knowledge.py   # 知识检索（Tavily）
│   ├── agent.py       # LangGraph Agent 核心逻辑
│   └── main.py        # FastAPI 入口
├── .env               # 环境变量（不提交）
├── .env.example       # 环境变量模板
└── pyproject.toml     # 项目配置
```

## 代码规范

### 风格
- 使用 **中文注释** 和 docstring
- 遵循 PEP 8，但行宽放宽到 100
- 类型注解必须写

### 命名
- 函数/变量: `snake_case`
- 类: `PascalCase`
- 常量: `UPPER_SNAKE_CASE`

### 导入顺序
1. 标准库
2. 第三方库
3. 本地模块

## Agent 架构

```
START → check → retrieve → generate → reflect → finalize → END
                    ↑                      ↓
                    └──── (不满意时循环) ────┘
```

### 节点说明
- **check**: 判断是否需要检索外部知识
- **retrieve**: 调用 Tavily 搜索
- **generate**: 用 DeepSeek 生成回答
- **reflect**: 自我评估回答质量
- **finalize**: 输出最终结果

### 状态字段
```python
class AgentState(TypedDict):
    messages: list              # 对话历史
    knowledge_context: str      # 检索到的知识
    need_knowledge: bool        # 是否需要检索
    current_answer: str         # 当前生成的回答
    reflection: str             # 反思意见
    is_satisfied: bool          # 是否满意当前回答
    iteration: int              # 当前迭代轮次
```

## API 接口

| 端点 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 健康检查 |
| `/health` | GET | 健康检查 |
| `/chat` | POST | 聊天（非流式） |
| `/chat/stream` | POST | 聊天（SSE 流式） |

## 开发指南

### 运行开发服务器
```bash
cd ~/rag-test
uv run python -m app.main
```

### 添加新节点
1. 在 `agent.py` 中定义节点函数
2. 用 `graph.add_node()` 注册
3. 用 `graph.add_edge()` 或 `add_conditional_edges()` 连接

### 添加新工具
1. 在 `app/` 下创建新模块
2. 在 `agent.py` 中导入并集成

## 注意事项

- `.env` 包含敏感信息，**绝不提交**
- 修改 Agent 流程后务必测试 `/chat/stream` 确认步骤正确
- `MAX_ITERATIONS = 3` 防止反思死循环，按需调整
