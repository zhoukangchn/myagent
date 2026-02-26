# OpenClaw 扩展机制速记：Plugin / Tool / Skill（调研整理）

> 目标：用一页纸搞清 OpenClaw 里“插件到底是啥”、能扩展哪些能力、什么时候该用 plugin 而不是只写 skill/定时任务。

## TL;DR（一句话）
- **Tool call**：模型调用的“函数接口”（一次调用、参数固定、返回结构化结果）。
- **Skill**：指导模型做事的“流程/SOP/提示词+清单”，本身不新增系统能力。
- **Plugin（插件/extension）**：**在 Gateway 进程内加载的一段扩展代码**，用来**新增系统能力面（tool surface / channel / service / CLI / provider auth / skills 打包）**。

三者关系：**Plugin 可以提供 Tool/Skill；Skill 编排调用 Tool；Tool 是能力执行的最小单位。**

> ✅ 核心结论（系统视角）：**skill + 脚本扩展的是“任务实现方式/工作流”，不是 OpenClaw 的“工具面（tool surface）”**；本质仍是在使用既有工具（如 `exec`）去运行外部进程。

---

## Plugin 是什么（精确定义）
OpenClaw 的 Plugin（也叫 Extensions）是 Gateway 启动时加载的模块（TypeScript/JavaScript），它可以向 OpenClaw **注册新能力**。

关键点：
- **运行位置**：在 **Gateway 进程内（in-process）**，所以插件等同“受信代码”，需要治理。
- **配置校验**：每个插件必须带 `openclaw.plugin.json`（manifest），其中包含 `configSchema`（JSON Schema）。
  - OpenClaw 可以在**不执行插件代码**的情况下校验配置（严格验证、避免乱配导致崩溃）。

---

## Plugin 能扩展哪些能力（分类 + 例子）
> 粗分两大类：**渠道扩展插件（接到哪里）** + **功能增强插件（能做什么）**。

### A) 渠道扩展插件（Channel plugins）
- 目标：接入新的消息平台/通信渠道，让 OpenClaw 能收发消息、处理线程/群组等。
- 配置位置通常在：`channels.<id>...`（而不是 `plugins.entries`）。

例子（以本机 `openclaw plugins list` 能看到的为准）：
- **discord**（已加载）
- **telegram**（已加载）
- **signal / whatsapp / slack / msteams / matrix / irc ...**（多数是 bundled，默认 disabled，需要启用或安装）

### B) 功能增强插件（Capability / Tools / Integrations）
- 目标：给 OpenClaw 增加新能力（新 tool、后台服务、命令、浏览器/语音/记忆等模块）。

常见子类：
1) **Agent Tools**（最常见）
   - 例：`jira_create_ticket`、`cmdb_lookup`、`deploy_service`（你们公司集成常落在这类）。
   - 优点：参数强约束（schema）、返回结构稳定、易做 allowlist/最小权限。
2) **后台服务 / 监听 / Webhook（事件驱动）**
   - 例：接收告警 webhook、消费队列、WebSocket、长期 polling。
3) **CLI 命令**
   - 例：增加 `openclaw xxx` 用于诊断/导入/同步/批处理。
4) **Provider/Auth 插件（模型鉴权）**
   - 例：把 OAuth/device login/API key 管理接进 OpenClaw。
5) **Skills 打包分发**
   - 插件 manifest 列出 skill 目录，把“能力 + SOP”一起交付。
   - 注意：**Skill 也能做到安装一致**（同一份 SKILL.md/脚本分发给所有人），但它保证的是 SOP/流程一致；
     Plugin 更像交付“稳定接口 + 最小权限 + 可运维”。

---

## 什么时候必须上 Plugin？什么时候先 Skill/Cron 就够？
### 先用 Skill/Cron 就够（PoC/个人效率优先）
- 只是把流程写稳、输出一致 → **Skill**
- 只是定时汇总/轮询检查 → **Cron**
- 只是 PoC，短期个人用 → Skill + 现有通用 tools（如 exec/web_fetch/message/browser）

### 更应该写成 Plugin 的信号（公司交付常见）
- 需要 **最小权限**（不想放开 `exec` 这种大杀器）
- 需要 **强参数约束 + 稳定结构化返回**（schema）
- 需要 **事件驱动监听/webhook/常驻连接**（而不是轮询）
- 需要 **可运维/可交付**：启用/禁用、doctor 排错、版本管理、回滚、日志/观测
- 需要 **团队复用**：同事装上就能用，不靠“会写 prompt 的那个人”

---

## 例子 1：camofox-browser（功能增强插件：反检测浏览器能力底座）
`camofox-browser` 把 **Camoufox/反检测浏览器自动化**接进 OpenClaw，常用于：渲染/滚动加载/分页/点击输入 + 更抗风控。

你能从它看到 plugin 的典型治理面：
- 有自己的 `configSchema`（url/port/autoStart/maxSessions/...）
- 可能被 `plugins.allow` 白名单拦（例如 `not in allowlist`）

### 和 OpenClaw 自带 `browser` tool（agent-browser）对比（关键点）
- **browser tool**：官方自带，主打通用网页自动化（Chromium 系 + CDP/Playwright）。
  - 依赖真实 Chromium 环境。
  - `chrome` profile 会涉及 Chrome 扩展 relay + 手动 attach tab。
- **camofox-browser**：Firefox/Camoufox 路线，更偏反检测专项。

经验法则：日常用 `browser`；遇强反爬再上 `camofox`。

---

## 例子 2：x-profile-analyzer（Skill：消费 camofox 能力做一个任务）
`x-profile-analyzer` 是 **Skill + Python 脚本**，用于分析 X/Twitter 用户画像。

关键点：
- 它本身**不是 Gateway plugin**，不会新增系统能力；它是把任务流程固化成 SOP。
- 它抓取阶段通常要求本机 `http://localhost:9377` 的 camofox server 可用（用于 Nitter 翻页/分页）。

一句话：**Plugin 提供能力底座（camofox）；Skill 消费能力完成具体任务（x-profile-analyzer）。**

---

## 例子 3：Channel 插件 vs message tool（用现成 Discord 讲清楚）
- **discord（channel 插件）**：负责“怎么把消息真正发到 Discord/怎么接收事件”。
- **message（tool）**：agent 调用的统一 API（例如 `message.send`），背后会路由到当前 channel（这里就是 Discord）。

---

## 官方口径（引用点，方便写公司文档）
- 插件系统总览：`docs/tools/plugin.md` / <https://docs.openclaw.ai/tools/plugin>
- 插件 manifest + schema（强校验来源）：`docs/plugins/manifest.md` / <https://docs.openclaw.ai/plugins/manifest>
- 插件管理命令（install/enable/doctor）：`docs/cli/plugins.md` / <https://docs.openclaw.ai/cli/plugins>
- Browser tool（自带浏览器能力定义）：`docs/tools/browser.md` / <https://docs.openclaw.ai/tools/browser>
- Chrome 扩展接管机制：`docs/tools/chrome-extension.md` / <https://docs.openclaw.ai/tools/chrome-extension>

---

## ChatGPT 对话交叉核对（Openclaw 插件介绍）
结论：**整体方向正确，可采纳约 80-90%**，但公司文档建议统一按官方术语落地。

可直接采纳：
- Plugin 是可安装扩展模块，用来给 OpenClaw 增加核心之外能力。
- 常见扩展面：Channel、Tools/Integrations、CLI/Gateway 扩展。
- 工程关键项：`openclaw.plugin.json`（含 `configSchema`）+ `package.json` 的 `openclaw.extensions`。

建议避免：
- 把第三方社区案例写成官方能力（需标注“社区/第三方”）。
- 把未确认的 hook 名称写死。

---

## 相关命令（记忆用）
- `openclaw plugins list`
- `openclaw plugins info <id>`
- `openclaw plugins enable <id>` / `disable <id>`
- `openclaw plugins doctor`
- `openclaw plugins install <npm包|本地路径>`（装完通常要重启 Gateway）
