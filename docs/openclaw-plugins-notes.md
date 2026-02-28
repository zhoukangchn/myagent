# OpenClaw 扩展机制（会议讲稿版）：Plugin / Tool / Skill

> 目标：给领导在会上讲清楚：**OpenClaw 的扩展机制是什么、为什么可控、怎么落地到企业集成**。

---

## 0. 一句话结论（开场 30 秒）
- **Plugin 扩展“系统能力面”**：把外部系统接进 OpenClaw，并提供可治理的一等工具接口（tools）。
- **Skill 扩展“任务方法论”**：把 SOP/策略/格式注入模型，让模型稳定、可控地使用工具。
- **Tool call 是运行时执行点**：模型发起结构化调用 → 系统路由到 plugin 实现 → 返回结构化结果 → 模型再组织输出。

> 领导可理解版：**Plugin 负责“接入与执行”，Skill 负责“流程与约束”。**

---

## 1. 关键概念（用企业系统语言解释）

### 1.1 Tool / Tool call（接口与调用）
- **Tool（工具接口）**：面向模型暴露的“函数 API”，有参数 schema、类型校验、可观测输出。
- **Tool call（一次调用）**：运行时的一次 API 调用，天然可记录/审计/限流。

### 1.2 Skill（流程治理层）
Skill 是“把人类 SOP 变成模型可执行策略”的载体，通常包含：
- 任务策略：先问什么、再查什么、如何判断完成
- 工具选择与参数约束：何时用哪个 tool、必填参数、边界条件
- 失败与降级：重试/换数据源/转人工/追加确认
- 输出规范：对齐业务口径（要点/表格/JSON/工单模板）

> 企业价值：Skill 让输出更稳定、可复用、可培训（新人上手快）。

### 1.3 Plugin（系统能力层 / 集成层）
Plugin 是 Gateway 内加载的扩展模块，提供两类价值：

**(A) 启动/加载阶段：构建“可运行的能力底座”**
- 注册 tools（把接口挂出来）
- 初始化依赖：鉴权、HTTP client、重试、限流、日志、数据库/队列连接等
- 配置强校验：典型通过 `openclaw.plugin.json` 的 `configSchema` 做 schema 校验（避免“配置错导致运行时炸”）

**(B) 运行时阶段：承接并执行 tool call**
- OpenClaw 将 tool call 路由到 plugin 的具体实现
- plugin 执行外部调用/读写/计算 → 返回结构化结果

> 企业价值：Plugin 把不稳定的外部系统集成收敛成**可治理的接口**（可审计、可限流、可重试、可统一鉴权）。

---

## 2. 一条调用链讲清“谁在什么时候干活”（核心图）

以“查天气”为例（业务系统可替换成 Jira/CMDB/发布平台）：

1) 系统注入 Weather Skill（流程与约束）
2) 模型发起 tool call：`get_weather(city, date)`
3) OpenClaw 路由调用 → Weather plugin 的工具实现
4) plugin 在运行时请求外部 API（鉴权/重试/限流/日志）
5) 返回结构化结果 → 模型按 Skill 的格式输出给用户

> 关键点：**Plugin 不是只在启动时干活；真正执行发生在 tool call 的运行时。**

---

## 3. 为什么这套机制适合企业（治理视角 3 点）

### 3.1 边界清晰：能力与流程分层
- plugin：把外部系统能力“产品化”为工具接口（能做什么）
- skill：把业务策略“标准化”为可复用 SOP（怎么做才对）

### 3.2 可控：结构化接口 + 强校验
- tool schema：参数可校验、返回可结构化处理
- plugin configSchema：配置变更可验证（减少线上事故）

### 3.3 可运维：可观测 + 失败处理集中化
- 统一的重试、限流、日志、指标（在 plugin 层集中做）
- tool call 天然是审计点（谁在什么时候调用了什么外部能力）

---

## 4. 什么时候只用 Skill？什么时候必须上 Plugin？（决策规则）

### 4.1 只用 Skill（PoC/流程编排）
满足任意：
- 目标是 SOP 固化（汇总/报告/信息抽取/通知）
- 能用已有工具完成（browser/web_fetch/message/exec 等）
- 可接受一定不确定性 + 人工兜底

### 4.2 必须用 Plugin（系统能力增量）
满足任意：
- 要新增“一等工具接口”（带 schema、可治理），而不是 `exec + 脚本` 临时拼
- 接入新渠道（新消息平台）
- 常驻服务/事件驱动入口（webhook/队列 consumer/poller）
- 替换系统级模块（slots：memory/检索等）
- 把鉴权/登录做成系统级能力（provider/auth）

> 推荐落地路线：**先 Skill 跑通价值 → 把最核心/最危险的外部集成升级成 Plugin tool**。

---

## 5. 企业落地建议（你在会上可以直接讲的 4 步）

1) **选 1 个高频、低风险场景**（例如：知识库查询 / 工单草拟 / 值班信息汇总）先做 skill
2) **把关键外部集成收敛为 tool（plugin 实现）**：CMDB/Jira/发布平台/告警系统
3) **把业务口径沉淀为 skills**：不同团队/不同输出模板
4) **治理与运维**：
   - tool schema 评审 + plugin 配置 schema 校验
   - 日志/指标/限流/审计（tool call）
   - 渐进式灰度：PoC → 小范围 → 全量

---

## 6. 现场 Q&A 备答（高频问题）

**Q1：Skill 能不能替代 Plugin？**
- 不能。Skill 只能教模型怎么用既有能力；Plugin 才能把外部系统变成“可调用、可治理”的一等能力。

**Q2：为什么不直接 exec 跑脚本？**
- PoC 可以；但长期治理差：参数/返回不稳定、权限边界弱、审计困难。做成 tool（plugin）后可 schema 化、可观测、可限流。

**Q3：Plugin 风险在哪里？**
- in-process 受信代码，必须版本治理/依赖控制/权限最小化；好处是把风险集中在少数可审计的接口里。

---

## 7. 相关命令 / 文档（备用）
- `openclaw plugins list`
- `openclaw plugins info <id>`
- `openclaw plugins enable <id>` / `disable <id>`
- `openclaw plugins doctor`

文档：<https://docs.openclaw.ai/cli/plugins>
