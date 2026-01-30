# SRE Agent Directory Structure

```
rag-test/
├── src/
│   ├── app/                        # 现有 RAG Agent (保持不变)
│   │   ├── agents/
│   │   ├── api/
│   │   ├── core/
│   │   └── services/
│   │
│   └── sre/                        # 新增 SRE Agent 模块
│       ├── __init__.py
│       │
│       ├── agents/                 # Multi-Agent 系统
│       │   ├── __init__.py
│       │   ├── supervisor/         # Supervisor Agent
│       │   │   ├── __init__.py
│       │   │   ├── graph.py        # Supervisor 流程图
│       │   │   ├── nodes.py        # Supervisor 节点逻辑
│       │   │   └── router.py       # 路由决策逻辑
│       │   │
│       │   ├── monitor/            # Monitor Agent
│       │   │   ├── __init__.py
│       │   │   ├── graph.py
│       │   │   ├── nodes.py
│       │   │   └── prompts.py      # Monitor 专用 prompts
│       │   │
│       │   ├── diagnoser/          # Diagnoser Agent
│       │   │   ├── __init__.py
│       │   │   ├── graph.py
│       │   │   ├── nodes.py
│       │   │   └── prompts.py
│       │   │
│       │   ├── executor/           # Executor Agent
│       │   │   ├── __init__.py
│       │   │   ├── graph.py
│       │   │   ├── nodes.py
│       │   │   └── prompts.py
│       │   │
│       │   └── shared/             # 跨 Agent 共享
│       │       ├── __init__.py
│       │       ├── state.py        # SRE 全局状态定义
│       │       ├── knowledge/      # 知识检索模块
│       │       │   ├── __init__.py
│       │       │   ├── base.py     # 知识源基类
│       │       │   ├── vector_store.py
│       │       │   ├── runbooks.py # Runbook 检索
│       │       │   └── incidents.py # 历史事件检索
│       │       └── tools/          # 工具注册表
│       │           ├── __init__.py
│       │           ├── registry.py # 工具注册管理
│       │           ├── base.py     # 工具基类
│       │           └── kubernetes/ # K8s 工具集
│       │               ├── __init__.py
│       │               ├── query.py    # 查询类
│       │               └── remediation.py # 修复类
│       │
│       ├── api/                    # SRE API 层
│       │   ├── __init__.py
│       │   ├── app.py              # FastAPI App 工厂
│       │   ├── schemas.py          # Pydantic 模型
│       │   ├── dependencies.py     # 依赖注入
│       │   └── routes/
│       │       ├── __init__.py
│       │       ├── health.py
│       │       ├── incidents.py    # 事件管理
│       │       ├── diagnose.py     # 诊断接口
│       │       ├── execute.py      # 工具执行
│       │       └── stream.py       # SSE 流接口
│       │
│       ├── core/                   # SRE 核心配置
│       │   ├── __init__.py
│       │   ├── config.py           # SRE 专用配置
│       │   ├── logging.py          # 结构化日志
│       │   ├── approval.py         # 审批状态管理
│       │   ├── state_machine.py    # 事件状态机
│       │   └── prompts/            # 系统级 prompts
│       │       ├── supervisor.md
│       │       ├── monitor.md
│       │       ├── diagnoser.md
│       │       └── executor.md
│       │
│       ├── services/               # SRE 服务层
│       │   ├── __init__.py
│       │   ├── llm.py              # LLM 服务 (可复用 app/services)
│       │   ├── log_analyzer.py     # 日志分析服务
│       │   ├── metrics.py          # 指标查询服务
│       │   ├── incident_manager.py # 事件生命周期管理
│       │   └── notification.py     # 通知服务
│       │
│       └── models/                 # 数据模型
│           ├── __init__.py
│           ├── incident.py         # 事件模型
│           ├── action.py           # 操作/工具模型
│           ├── diagnosis.py        # 诊断结果模型
│           └── enums.py            # 枚举定义
│
├── tests/
│   ├── app/                        # 现有测试
│   └── sre/                        # SRE 测试
│       ├── unit/
│       │   ├── agents/
│       │   │   ├── test_supervisor.py
│       │   │   ├── test_monitor.py
│       │   │   ├── test_diagnoser.py
│       │   │   └── test_executor.py
│       │   ├── services/
│       │   │   ├── test_log_analyzer.py
│       │   │   └── test_metrics.py
│       │   └── tools/
│       │       └── test_kubernetes_tools.py
│       ├── integration/
│       │   ├── test_incident_workflow.py
│       │   └── test_end_to_end.py
│       └── fixtures/
│           ├── logs/
│           ├── metrics/
│           └── runbooks/
│
├── docs/
│   ├── SRE_AGENT_ROADMAP.md        # 本文件
│   ├── architecture/
│   │   ├── 01-overview.md
│   │   ├── 02-supervisor.md
│   │   ├── 03-agents.md
│   │   ├── 04-tools.md
│   │   └── 05-api.md
│   └── runbooks/                   # 示例 Runbooks
│       ├── pod-crash-loop.md
│       ├── high-memory-usage.md
│       └── database-connection-pool.md
│
├── scripts/
│   ├── ingest_knowledge.py         # 知识库导入脚本
│   ├── simulate_alert.py           # 告警模拟脚本
│   └── benchmark.py                # 性能测试
│
├── knowledge/                      # 本地知识库
│   ├── runbooks/                   # SOP/Runbooks
│   ├── incidents/                  # 历史事件报告
│   └── docs/                       # 架构文档
│
├── .env                            # 环境变量
├── .env.sre.example                # SRE 环境变量模板
├── pyproject.toml
└── docker-compose.sre.yml          # SRE 服务编排
```

## Key Design Decisions

### 1. Agent 组织方式
每个 Agent 作为独立子包 (supervisor/, monitor/, diagnoser/, executor/)，包含：
- `graph.py` - 流程定义
- `nodes.py` - 节点逻辑
- `prompts.py` - 专属 prompts (可选)

### 2. 共享组件位置
- `shared/state.py` - 全局状态定义
- `shared/knowledge/` - 知识检索基础设施
- `shared/tools/` - 工具注册和分类

### 3. 服务复用策略
- LLM 服务: 优先复用 `src/app/services/llm.py`
- 配置管理: SRE 专用配置 `src/sre/core/config.py` 继承/扩展基础配置
- 日志: 复用 `src/app/core/logging.py`

### 4. API 设计
- 独立 FastAPI App (`src/sre/api/app.py`)
- 可单独部署，也可合并到主 App
- WebSocket 用于实时状态推送

### 5. 测试策略
- 单元测试: 每个 Agent 和 Service 独立测试
- 集成测试: 完整事件工作流测试
- Fixtures: 模拟日志、指标、Runbooks
