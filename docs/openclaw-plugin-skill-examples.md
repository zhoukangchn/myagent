# OpenClaw 插件与技能应用指南：典型应用案例与选型

> 本文档通过拆解不同 OpenClaw Plugin 类型，说明为何有时候仅需 Plugin，而有时候需附带 Skill，以及相关使用规范。这些真实案例能够辅助不同需求下的形态选型标准。

---

## 1. 仅有 Plugin（不需要 Skill）的案例

大量 Plugin 独立运行即满足需求——当 Tool Schema 本身足够清晰，或 Plugin 不暴露具体的 Agent 工具时，不需要额外引导 LLM。

### A1. Channel-only (完全纯通道插件)：`discord`
常见的入口驱动型插件。只注册消息通道与协议的连接，无 Tool 、无 Skill。
```json
{
  "id": "discord",
  "channels": ["discord"],
  "configSchema": { "type": "object", "additionalProperties": false, "properties": {} }
}
```
**为什么不需要 Skill**：Channel 的收发消息逻辑由底层的 Gateway 统一调度处理。大模型只需要关注"回复文本"或"触发工具"，它不需要理解“当前是通过 WebSocket 还是 Webhook 收发的 Discord 消息”。
*同类参考*：`telegram`、`slack`、`matrix`、`msteams` 等通道集成包。

### A2. Provider-auth-only (系统鉴权提供类)：`minimax-portal-auth`
仅注册第三方模型服务商（Provider）环境下的 OAuth 等完整原生鉴权流程。
```json
{
  "id": "minimax-portal-auth",
  "providers": ["minimax-portal"],
  "configSchema": { "type": "object", "additionalProperties": false, "properties": {} }
}
```
**为什么不需要 Skill**：登录与凭证保存是 CLI 级别的行为（如通过运行 `openclaw models auth login` 记录凭据），推理时会自动通过插件附加请求头凭证。大模型的逻辑层面根本不参与此流程。
*同类参考*：`google-gemini-cli-auth`、`copilot-proxy`。

### A3. Tool-only (自我表述完整、无需引导的纯工具)：`diffs`
注册到系统的供 LLM 获取的 Agent 工具，工具参数（文件位置、布局格式等）明确而易懂。
```json
{
  "id": "diffs",
  "name": "Diffs",
  "description": "面向 Agent 的只读文件差异对比器及图像渲染层。",
  "configSchema": { ... }
}
```
**为什么不需要 Skill**：工具传入的 Json Schema 对 `diffs` 的描述已经完全直白。LLM 只需看变量名就能明白其用途（如 `file_path`, `theme`），毫无门槛，不需要再在上下文中占据 Token 去教授使用方法。
*同类参考*：`llm-task`、`lobster`。

### A4. 核心基础设施组件：`memory-core`
系统内置组件，提供运行时的隐式存储或内存支持能力，底层自动调用。
```json
{
  "id": "memory-core",
  "kind": "memory",
  "configSchema": { "type": "object", "additionalProperties": false, "properties": {} }
}
```
**为什么不需要 Skill**：这些功能是由核心 Gateway 主动调用的挂载钩子（如 `auto-recall` 和历史快照）。模型既不需要感知，也不能手动决定使用方式。
*同类参考*：`memory-lancedb`、`diagnostics-otel`。

#### 【章节小结】
只有在系统要求“不需要大模型做针对性决策、依靠底层 Gateway 接管、或工具简单易懂”时，完全纯净的 Plugin 是最佳方案。

---

## 2. 带 Skill 的 Plugin (能力 + 手册并行) 的案例

当注册给模型的系统级别 Tool (工具) 极其复杂，或需要一套组合拳（先 A 后 B 的操作 SOP）时，单靠参数上的 Schema 是无力的，此时我们需要通过 Skill 对它做额外的使用说明指导。

### B1. Plugin + 1 个组合向导 Skill：`acpx` 工具（沙箱）
提供代码实验执行控制进程，并教导模型“应该选用哪种沙盒或如何回滚错漏”。

*   **Plugin 做了什么** (`index.ts`)：在 Gateway 注册 ACP Runtime Backend（后端进程控制管理），并向 LLM 提供 `sessions_spawn` 核心开启接口。
*   **Skill 做了什么** (`acp-router/SKILL.md`)：
    *   在意图上判断分析：面对各种错误状态，选择普通终端，还是重启底层的 ACP 容器沙箱？
    *   映射 Agent 角色以进行任务兜底等。

**为什么必须搭配 Skill**：`sessions_spawn` 的 Schema 只能描述它需要 `task_id` 和 `runtime`。但何时选择 `runtime="acp"`，容器启动失败怎样应对（错误兜底流程），这一系列决策依据**必须通过 Skill 以文字的方式硬塞进 Prompt 告诉大脑**。

### B2. Channel + 多重复杂应用 Skill 分组：`feishu` (飞书集成)
涉及多个复杂的文档块操作逻辑与不同的服务组合。

*   **Plugin 做了什么** (`index.ts`)：建立飞书长连接（Channel 收发管理），然后注册了 4 个模块：`feishu_doc`、`feishu_drive`、`feishu_wiki`、`feishu_perm`。
*   **Skill 做了什么**（下分 4 个具体的 `SKILL.md` 子模块）：
    *   `feishu-doc` 教大模型在使用飞书云文档 `doc` 的 Tool 时应该怎么按块格式发送和解析（包含多达 12 种子动作工作流示例及 JSON 参数标准）。
    *   同理分为：云盘上传向导、群组及权限管理指引手册。

**为什么拆分成 4 组 Skill**：飞书 API 的业务复杂度极高（尤其是区分 wiki 层和独立 doc 层，文档元素节点规则繁多等）。如果写在一个巨型 `SKILL.md` 中，每次触发都会占用极大量冗余的 Token 上下文窗口。通过 Plugin 目录的细颗粒拆分，系统会拦截相关的 `URL` 依据，精准按需加载只负责某一块领域的特定 Skill，保证了大模型认知的专注度。
