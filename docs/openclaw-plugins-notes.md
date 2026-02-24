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

## 相关命令（记忆用）
- `openclaw plugins list`
- `openclaw plugins info <id>`
- `openclaw plugins enable <id>` / `disable <id>`
- `openclaw plugins doctor`
- `openclaw plugins install <npm包|本地路径>`（装完通常要重启 Gateway）

