# SRE Agent Roadmap

## Overview

基于现有 RAG Agent 架构，扩展为 **Supervisor + Multi-Agent** 模式的 SRE (Site Reliability Engineering) Agent 系统。

**核心理念**: 监控发现问题 → 诊断定位根因 → 执行修复操作，全程 Human-in-the-Loop。

---

## 3-Phase Implementation Plan

### Phase 1: Observability & Knowledge (Weeks 1-2)

**目标**: 构建可观测性基础设施和知识检索能力

#### 1.1 知识库 RAG 扩展
- **任务**: 扩展 `knowledge.py` 支持多种数据源
  - SRE Runbooks (Markdown/PDF)
  - 历史 Incident Reports
  - 架构文档 (Confluence/Notion API)
  - 错误码知识库
- **实现**: 
  - 新增 `src/sre/agents/shared/knowledge/` 模块
  - 向量存储 (ChromaDB/Qdrant) 索引文档
  - 混合检索：向量相似度 + BM25 关键词匹配

#### 1.2 日志分析服务
- **任务**: 创建 `log_analyzer.py` 服务
  - 支持多种日志格式 (JSON, CSV, Plain text)
  - 异常模式识别 (使用 LLM + Regex 规则)
  - 日志聚类和摘要
- **API**: 
  - `POST /logs/analyze` - 上传日志文件分析
  - `POST /logs/query` - 自然语言查询日志

#### 1.3 指标接入
- **任务**: Metrics 收集器
  - Prometheus API 客户端
  - 基础指标缓存和查询
- **实现**: `src/sre/services/metrics.py`

**Phase 1 交付物**:
- [ ] 多源知识检索服务
- [ ] 日志分析接口
- [ ] 指标查询接口
- [ ] 集成测试覆盖

---

### Phase 2: Diagnostic Reasoning (Weeks 3-4)

**目标**: 实现 Multi-Agent 诊断工作流

#### 2.1 Agent 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                        Supervisor                           │
│  (Incident Manager - 协调决策)                                │
└──────────────┬──────────────────────────────┬───────────────┘
               │                              │
               ▼                              ▼
┌───────────────────────┐      ┌───────────────────────┐
│       Monitor         │      │      Diagnoser        │
│  (异常检测 & 信息收集)  │      │  (根因分析 & 知识检索) │
│                       │      │                       │
│ • 指标阈值检查         │      │ • 查询知识库           │
│ • 日志异常扫描         │      │ • 关联分析             │
│ • 告警聚合             │      │ • 生成诊断报告          │
└───────────┬───────────┘      └───────────┬───────────┘
           │                              │
           └──────────────┬───────────────┘
                          ▼
              ┌───────────────────────┐
              │       Executor        │
              │  (操作执行 & 验证)      │
              │                       │
              │ • 查询类工具执行       │
              │ • 修复类工具等待审批   │
              │ • 执行结果验证         │
              └───────────────────────┘
```

#### 2.2 核心组件实现

**A. Supervisor Agent**
- **职责**: 接收告警/用户请求，决策下一步行动
- **状态机管理**:
  ```
  ALERT_RECEIVED → GATHERING_INFO → DIAGNOSING → 
  AWAITING_DECISION → EXECUTING → VERIFYING → RESOLVED
  ```
- **路由逻辑**: 根据当前状态调用子 Agent

**B. Monitor Agent**
- **职责**: 收集和整理可观测性数据
- **节点**:
  - `fetch_metrics`: 拉取相关指标
  - `analyze_logs`: 分析关联日志
  - `gather_context`: 整合时间和环境信息

**C. Diagnoser Agent**
- **职责**: 分析根因，生成诊断报告
- **节点**:
  - `query_knowledge`: RAG 查询相关知识
  - `analyze_correlation`: 关联指标-日志-事件
  - `generate_hypothesis`: 生成可能的根因假设
  - `reflect_diagnosis`: 自我验证诊断完整性

**D. Executor Agent**
- **职责**: 执行诊断和修复操作
- **节点**:
  - `plan_actions`: 制定操作计划
  - `execute_tool`: 执行具体工具 (查询类自动，修改类需审批)
  - `verify_result`: 验证操作效果

#### 2.3 工作流实现

**LangGraph 状态设计**:
```python
class SREState(TypedDict):
    # 事件信息
    incident_id: str
    alert_source: str
    severity: str
    
    # 收集的数据
    metrics_data: dict
    log_summary: str
    knowledge_context: str
    
    # 诊断结果
    diagnosis_report: str
    root_cause_hypotheses: list[str]
    confidence_score: float
    
    # 执行计划
    action_plan: list[ActionItem]
    pending_approval: list[ActionItem]  # 需人工审批
    executed_actions: list[ActionResult]
    
    # 状态机
    status: Literal["monitoring", "diagnosing", "awaiting_approval", 
                    "executing", "verifying", "resolved", "escalated"]
    
    # 循环控制
    iteration: int
    max_iterations: int
```

**Phase 2 交付物**:
- [ ] Supervisor + 3 个子 Agent 实现
- [ ] Multi-Agent 协作工作流
- [ ] 状态机管理和路由逻辑
- [ ] 诊断报告生成

---

### Phase 3: Action & Remediation (Weeks 5-6)

**目标**: 实现安全可控的自动化修复能力

#### 3.1 Tool Framework

**工具分类**:
```python
class ToolCategory(Enum):
    QUERY = "query"       # 纯查询，自动执行
    DIAGNOSTIC = "diagnostic"  # 诊断命令，自动执行
    REMEDIATION = "remediation"  # 修复操作，需审批
    DESTRUCTIVE = "destructive"  # 高危操作，需二次确认
```

**工具注册示例**:
```python
@sre_tool(category=ToolCategory.QUERY, description="查询 Pod 日志")
async def get_pod_logs(pod_name: str, namespace: str, tail: int = 100) -> str:
    ...

@sre_tool(category=ToolCategory.REMEDIATION, description="重启 Pod", 
          requires_approval=True)
async def restart_pod(pod_name: str, namespace: str) -> ActionResult:
    ...

@sre_tool(category=ToolCategory.DESTRUCTIVE, description="删除 PVC",
          requires_approval=True, dangerous=True)
async def delete_pvc(name: str, namespace: str) -> ActionResult:
    ...
```

#### 3.2 Human-in-the-Loop 机制

**审批流程**:
1. Executor 生成修复计划
2. 高风险操作自动标记为 `pending_approval`
3. 通过 API/WebSocket 推送审批请求
4. 用户审批后 (`POST /incidents/{id}/approve`) 继续执行
5. 超时未审批自动升级 (Escalation)

**实现**:
- `src/sre/api/routes/incidents.py` - 事件管理接口
- `src/sre/core/approval.py` - 审批状态管理
- WebSocket `/ws/incidents` - 实时通知

#### 3.3 安全防护

- **沙箱执行**: 危险命令在受限环境中执行
- **变更回滚**: 自动快照，支持快速回滚
- **影响范围分析**: 执行前评估影响范围
- **审计日志**: 所有操作记录完整审计链

#### 3.4 集成接口

**REST API**:
```
POST   /incidents                 # 创建事件 (告警接入)
GET    /incidents/{id}            # 获取事件详情
POST   /incidents/{id}/approve    # 审批待执行操作
POST   /incidents/{id}/escalate   # 人工升级
GET    /incidents/{id}/stream     # SSE 实时状态流
GET    /diagnose                  # 主动诊断接口
POST   /execute                   # 执行工具 (带审批)
```

**Phase 3 交付物**:
- [ ] Tool Framework 和工具库
- [ ] 审批工作流实现
- [ ] WebSocket 实时通知
- [ ] 安全防护机制
- [ ] 完整 API 接口

---

## Success Metrics

| 阶段 | KPI | 目标值 |
|------|-----|--------|
| Phase 1 | 知识检索准确率 | > 85% |
| Phase 1 | 日志异常检测召回率 | > 80% |
| Phase 2 | 根因诊断准确率 | > 70% |
| Phase 2 | 平均诊断时间 | < 2 min |
| Phase 3 | 自动化修复成功率 | > 60% |
| Phase 3 | 人工审批响应时间 | < 5 min |

---

## Risk Mitigation

1. **过度自动化风险**: 所有修复操作默认需审批，逐步放开
2. **误诊风险**: 诊断结果必须包含置信度，低置信度自动升级人工
3. **权限风险**: 工具执行使用最小权限原则，敏感操作多重验证
4. **知识库过时**: 建立知识库版本管理和更新机制

---

## Integration with Existing Codebase

本项目将保留现有 `src/app/agents/` 的 RAG Agent，作为独立模块。
新的 SRE Agent 将放在 `src/sre/` 目录下，两者可共用：
- `src/app/core/config.py` - 配置管理
- `src/app/core/logging.py` - 日志配置
- `src/app/services/llm.py` - LLM 服务
- `src/app/services/knowledge.py` - 知识检索 (需扩展)

