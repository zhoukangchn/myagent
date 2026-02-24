# OpenClaw 扩展机制速记：Plugin / Tool / Skill（调研整理）

> 目标：用一页纸搞清 OpenClaw 里“插件到底是啥”、能扩展哪些能力、什么时候该用 plugin 而不是只写 skill/定时任务。

## 一句话结论
- **Tool call**：模型调用的“函数接口”（一次调用、参数固定、返回结构化结果）。
- **Skill**：指导模型做事的“流程/SOP/提示词+清单”，本身不新增系统能力。
- **Plugin（插件/extension）**：**在 Gateway 进程内加载的一段扩展代码**，用来**新增系统能力**（注册 tools、后台服务、CLI 命令、channel、provider auth、skills 等）。

三者关系：**Plugin 可以提供 Tool/Skill；Skill 组合调用 Tool；Tool 是能力执行的最小单位。**

---

## Plugin 是什么（精确定义）
OpenClaw 的 Plugin（也叫 extension）是 Gateway 启动时加载的模块（TypeScript/JavaScript），它可以向 OpenClaw **注册新能力**。

关键点：
- **运行位置**：在 **Gateway 进程内（in-process）**，所以插件等同“受信代码”，需要治理。
- **配置校验**：每个插件必须带 `openclaw.plugin.json`（manifest），其中包含 `configSchema`（JSON Schema）。
  - OpenClaw 可以在**不执行插件代码**的情况下校验配置（严格验证、避免乱配导致崩溃）。

---

## Plugin 能扩展哪些能力（分类）
### 1) Agent Tools（最常见的扩展）
- 注册自定义工具（函数）：例如 `jira_create_ticket`、`cmdb_lookup`、`deploy_service`。
- 优点：
  - 参数强约束（JSON schema）
  - 返回结构稳定
  - 更容易做 allowlist/最小权限（比把 `exec` 放开安全很多）

### 2) 后台服务 / 监听 / Webhook（事件驱动）
- 常驻逻辑：消费队列、WebSocket、接收告警回调、对外提供 webhook endpoint。
- 适合：事件驱动系统集成（比 cron 轮询更自然、延迟更低）。

### 3) CLI 命令
- 新增 `openclaw xxx` 类命令，用于诊断、导入、同步、批处理。
- 适合：把能力变成“确定性入口”，可在 CI/脚本里用。

### 4) Channel 插件（聊天平台）
- 接入新的聊天平台或扩展其能力；配置一般在 `channels.<id>...`。

### 5) Provider/Auth 插件（模型鉴权）
- 把 OAuth/device login/API key 管理接进 OpenClaw（`openclaw models auth ...`）。

### 6) Skills 打包分发
- 插件 manifest 可以列出 skill 目录，把“能力 + SOP”一起交付。

---

## 什么时候必须上 Plugin？什么时候先 Skill/Cron 就够？
### 可以先不写插件（Skill/Cron 先验证价值）
- 只是想把提示词流程写稳、输出一致 → **Skill**
- 只是定时汇总/轮询检查（每小时/每天） → **Cron**
- 只是 PoC，短期个人用，安全要求不高 → Skill + 现有通用工具（如 exec/web_fetch/message）

### 更应该写成 Plugin 的信号（产品化/公司交付常见）
- 需要 **最小权限**（不想放开 `exec` 这种大杀器）
- 需要 **强参数约束 + 稳定结构化返回**（schema）
- 需要 **事件驱动监听/webhook/常驻连接**（而不是轮询）
- 需要 **可运维/可交付**：启用/禁用、doctor 排错、版本管理、回滚、日志/观测
- 需要 **多人复用**：同事装上就能用，不靠复制脚本和 prompt

---

## 治理与安全（公司最关心）
- Plugin 是 in-process 代码：等同引入依赖，必须当“受信软件”管理。
- 推荐策略：
  - 使用 `plugins.allow` 白名单（deny 优先）
  - 插件配置用 JSON Schema 严格校验
  - 依赖安装默认 `--ignore-scripts`（降低 supply-chain 风险）
  - 对外 webhook 要做签名校验 / host allowlist / 反重放

---

## 最小可行实验（MVP）建议
1) **新增一个 tool 的插件**（最快验证插件机制）：
   - 输入：一段文本/JSON
   - 输出：结构化结果 + 让 agent 写总结
2) **受控 HTTP 工具**（模拟接公司 API）：
   - 只允许访问白名单域名
   - token 放在插件 config（标记敏感字段）
3) **Webhook listener**（更贴近告警/工单回调）：
   - `POST /hook` → 记录事件/发消息/触发流程

---

## 例子：camofox-browser（用插件把“浏览器自动化”接进来）
`camofox-browser` 是一个典型的“功能型插件”：它把 **Camoufox/反检测浏览器自动化**接进 OpenClaw。

它解决的核心问题：
- **需要真实浏览器行为**的自动化（渲染、滚动加载、分页、点击、输入等），比纯 HTTP 抓取更通用。
- 在一些站点上，**比普通 headless 更不容易被识别/封锁**（反爬/风控场景更稳）。
- 把浏览器能力做成**可治理的服务组件**：可配置、可限流、可控并发、可回收会话。

### 和 OpenClaw 自带的 browser tool（agent-browser）怎么选？
> OpenClaw 自带的“浏览器能力”通常指 `browser` tool（OpenClaw-managed Chromium + Playwright/CDP + 可选 Chrome 扩展接管）。

对比要点：
- **定位**
  - `browser` tool：通用网页自动化/验证，覆盖面广（打开页面、点/填、截图、PDF、读可访问树）。
  - `camofox-browser`：更偏“反检测/风控更严的网站”的浏览器自动化能力底座。
- **依赖与“授权/接管”模型（很容易被误解）**
  - `browser` tool **需要真实浏览器环境**：控制的是 Chromium 系（Chrome/Brave/Edge/Chromium）。系统上没有可用浏览器/相关依赖时会失败或功能受限。
  - `browser` tool 有两种常见控制模式：
    - `openclaw` profile：OpenClaw 启动一个**隔离的专用浏览器 profile**（不接管你的日常浏览器）。你需要做的是“在这个 profile 里登录网站账号”（属于网站登录，不是控制授权）。
    - `chrome` profile：通过 **Chrome 扩展 Relay 接管你现有 Chrome tab**。这时需要你在目标 tab 上点击扩展按钮 **Attach**（badge 显示 `ON`），明确授权控制该 tab。
- **浏览器内核**
  - `browser` tool：Chromium 系 + CDP/Playwright（功能一等公民，集成度高）。
  - `camofox-browser`：Firefox 系（Camoufox/Camoufox server，目标是更抗检测）。
- **抗检测能力**
  - `browser` tool：强在可控与功能完整；对强风控站点可能更容易被识别。
  - `camofox-browser`：优势通常在“更像真人”，用于绕开/缓解反爬。
- **运维与生态**
  - `browser` tool：OpenClaw 官方一等公民（profiles、截图/快照/act、扩展接管、节点代理等都集成得更完整）。
  - `camofox-browser`：作为插件提供“另一条浏览器路线”，适合当某些站点的专项武器。

经验法则：
- 日常自动化/信息采集：优先用 **`browser` tool**。
- 遇到强反爬、Chromium 更容易被拦的场景：再考虑 **`camofox-browser`**（或让 Skill 在失败时降级切换）。

你能从这个例子理解三件事：
1) **插件提供能力**：它不是 prompt，而是 Gateway 加载后提供一整套能力（可能包含 tool、服务配置、连接管理等）。
2) **配置可治理**：它有自己的 `configSchema`（例如 server URL、是否 autoStart、会话上限等），配置错了会在校验阶段被拦。
3) **allowlist 是安全阀**：在 `openclaw plugins list` 里如果看到类似 `error: not in allowlist`，说明插件虽然“可发现”，但被 `plugins.allow` 白名单策略挡住了（公司环境通常会这样做，避免随便加载本地插件）。

### 你本机上能看到的现象（示例）
- `openclaw plugins list --json` 显示 `camofox-browser`，但状态可能是 `disabled`，并伴随 `not in allowlist`。

### 这类插件一般怎么用（概念流程）
- 把插件加入允许列表（`plugins.allow`）
- 启用插件（`plugins.entries.camofox-browser.enabled = true` 或 `openclaw plugins enable camofox-browser`）
- 配置插件（例如 camofox server 的 `url/port/autoStart/maxSessions...`）
- 重启 Gateway 生效
- 然后它提供的“浏览器能力”才会以 tools/服务的形式对 agent 可用

> 备注：具体 tool 名称和调用方式取决于插件实现；重点是理解：**插件=接入一坨新能力 + 受 schema/allowlist/enable 治理**。

---

## 例子：x-profile-analyzer（Skill 依赖 camofox 能力，但它本身不是 Plugin）
`x-profile-analyzer` 是一个 **Skill + Python 脚本**，用于分析 X/Twitter 用户画像。

关键点：
- 它本身**不会给 OpenClaw 增加新系统能力**（不是 Gateway plugin），只是把“怎么抓数据、怎么分析、输出什么格式”固化成 SOP。
- 它在抓取阶段通常需要 **Camofox server** 可用（文档里写死了 `http://localhost:9377`，用于 Nitter 翻页/分页）。
  - 这意味着：从“能力依赖”角度，它依赖 camofox；
  - 但从“实现形态”角度，它不一定必须由 `camofox-browser` 插件来提供，只要同等的 camofox server 在本机可用即可。

一句话对比：
- `camofox-browser`：**Plugin**，把浏览器自动化能力“接进 OpenClaw 并可治理”。
- `x-profile-analyzer`：**Skill**，消费上述能力（或同等能力）完成一个具体任务。

---

## 官方口径（引用点，方便写公司文档）
OpenClaw 官方把插件称为 **Plugins (Extensions)**，定义为 **Gateway 进程内加载的扩展模块**。

建议引用以下官方文档页面（本地路径 / 线上链接二选一放到交付物里）：
- 插件系统总览：`docs/tools/plugin.md` / <https://docs.openclaw.ai/tools/plugin>
- 插件 manifest + schema（强校验来源）：`docs/plugins/manifest.md` / <https://docs.openclaw.ai/plugins/manifest>
- 插件管理命令（install/enable/doctor）：`docs/cli/plugins.md` / <https://docs.openclaw.ai/cli/plugins>
- Browser tool（自带浏览器能力定义）：`docs/tools/browser.md` / <https://docs.openclaw.ai/tools/browser>
- Chrome 扩展接管机制：`docs/tools/chrome-extension.md` / <https://docs.openclaw.ai/tools/chrome-extension>

---

## 相关命令（记忆用）
- `openclaw plugins list`
- `openclaw plugins info <id>`
- `openclaw plugins enable <id>` / `disable <id>`
- `openclaw plugins doctor`
- `openclaw plugins install <npm包|本地路径>`（装完通常要重启 Gateway）

