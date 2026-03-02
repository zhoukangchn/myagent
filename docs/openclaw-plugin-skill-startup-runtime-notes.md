# Plugin vs Skill：官方定义、对比与 Why

> 基于 [官方文档 docs.openclaw.ai/tools/plugin](https://docs.openclaw.ai/tools/plugin) + 社区讨论整理。
> 参考代码：`~/myagent/references/plugins-with-skills/`（acpx / feishu）

## 目录
1. [一、官方定义](#一官方定义)
2. [二、架构层别（宏观视角）](#二架构层别宏观视角)
3. [三、Why：为什么需要两层？](#三why为什么需要两层)
4. [四、核心属性对比](#四核心属性对比)
5. [五、启动时 vs 运行时（生命周期深度解析）](#五启动时-vs-运行时生命周期深度解析)
6. [六、真实例子解析](#六真实例子解析)
7. [七、Plugin 选型决策指南](#七plugin-选型决策指南)
8. [八、安全提示](#八安全提示)
9. [九、一句话总结（TL;DR）](#九一句话总结tldr)

---

## 一、官方定义

### Plugin（官方称 Extension）

> Plugins are small code modules that extend the core functionality of the AI assistant.

Plugin 是 **TypeScript 代码模块**，由 Gateway 在启动时加载执行。通过注册 API 向系统注入能力：

| 注册 API | 能力 | 例子 |
|----------|------|------|
| `api.registerProvider(...)` | 模型 provider + auth | minimax-portal-auth, google-gemini-cli-auth |
| `api.registerChannel(...)` | 消息通道 | telegram, discord, feishu, msteams |
| `api.registerTool(...)` | Agent tool | feishu_doc, voice_call |
| `api.registerHook(...)` | 事件钩子 | command:new 触发时执行逻辑 |
| `api.registerGatewayMethod(...)` | Gateway RPC 方法 | voicecall.status |
| `api.registerCli(...)` | CLI 命令 | `openclaw voicecall start` |
| `api.registerCommand(...)` | 自动回复命令（不经过 AI） | `/mystatus` 直接返回文本 |
| `api.registerService(...)` | 后台服务 | 长连接、轮询、定时任务 |

**Plugin 入口形式**（二选一）：
```typescript
// 函数形式
export default function register(api) { ... }

// 对象形式
export default { id, name, configSchema, register(api) { ... } }
```

### Skill

> Skills are Markdown documents that teach the AI agent how to use specific tools.

Skill 遵循 [AgentSkills](https://agentskills.io) 规范，以 **`SKILL.md`** 为入口，在会话中按需注入 LLM 上下文。Skill 通过提示词改变 LLM 的行为——教 LLM 什么时候触发、用什么参数、怎么处理错误。

Skill 还可以带 **`scripts/` 目录**，包含可执行脚本。LLM 读完 SKILL.md 后，可以通过系统内置的 `exec` tool 来调用这些脚本。

**Skill 典型结构**：
```
my-skill/
├── SKILL.md              ← 入口（必须，含 YAML frontmatter）
├── scripts/              ← 可选，可执行脚本
│   └── deploy.sh
└── references/           ← 可选，参考文档
    └── api-spec.md
```

**SKILL.md frontmatter**（[官方文档](https://docs.openclaw.ai/tools/skills#format-agentskills-+-pi-compatible)）：
```yaml
---
name: my-skill
description: 一句话描述
user-invocable: true            # 可选，暴露为用户 /slash 命令（默认 true）
disable-model-invocation: false # 可选，为 true 则不注入模型 prompt
command-dispatch: tool          # 可选，跳过模型直接调用 tool
command-tool: my_tool           # 可选，配合 command-dispatch 使用
metadata: { "openclaw": { "requires": { "bins": ["curl"], "env": ["API_KEY"] } } }
---
# 正文中可用 {baseDir} 引用 skill 目录路径
```

**Gating（加载时过滤）**：通过 `metadata.openclaw.requires` 控制 skill 是否加载：
- `bins` / `anyBins`：要求 PATH 中存在特定命令
- `env`：要求环境变量存在
- `config`：要求 `openclaw.json` 中特定配置为 truthy
- `os`：限定操作系统（darwin / linux / win32）

### Plugin 可以携带 Skill

官方文档明确说明：Plugin manifest 的 `"skills"` 字段可以列出 skill 目录，Plugin 充当 Skill 的容器和分发机制。

```json
{
  "id": "my-plugin",
  "skills": ["./skills"],
  "configSchema": { ... }
}
```

---

---

## 二、架构层别（宏观视角）

OpenClaw 采用 hub-and-spoke 架构，Gateway 是中心控制面。Plugin 和 Skill 分处不同层级：

```
┌─────────────────────────────────────────────────────────┐
│                    ① 用户层                              │
│  消息输入（Telegram / Discord / CLI / WebChat / Node）    │
└────────────────────────┬────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│              ② Gateway 控制面（系统层）                    │
│                                                          │
│  ▸ Channel Plugin   — 消息通道适配（WebSocket/Webhook）   │
│  ▸ Provider Plugin  — 模型路由 + OAuth 鉴权              │
│  ▸ Tool Plugin      — 注册 agent tool（代码实现）         │
│  ▸ Hook / Service   — 事件钩子、后台服务                  │
│  ▸ RPC / CLI        — Gateway 方法、命令行扩展            │
│                                                          │
│  【Plugin 代码运行在这一层：Gateway Node.js 进程内】       │
└────────────────────────┬────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│              ③ Agent Runtime（运行时层）                   │
│                                                          │
│  ▸ 组装上下文（session history + memory）                 │
│  ▸ 注入 Skill 提示词（匹配激活条件后加载 SKILL.md）       │
│  ▸ 调用 LLM 推理                                        │
│  ▸ 接收 tool call → 分发到 Plugin Tool 或系统内置 Tool    │
│                                                          │
│  【Skill 在这一层生效：注入 LLM 上下文，影响决策】        │
└────────────────────────┬────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│              ④ LLM + Skill 层（认知层）                   │
│                                                          │
│  ▸ LLM 推理（结合 Skill 提示词 + tool schema 做决策）     │
│  ▸ Skill 可带 scripts/，LLM 通过 exec 调用               │
│  ▸ 输出：tool call / 文本回复                             │
└────────────────────────┬────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│              ⑤ 执行层                                    │
│                                                          │
│  ▸ Plugin Tool  → Plugin 代码执行（② 层）                │
│  ▸ 系统内置 Tool → 系统内核（read/write/exec/web_fetch） │
│  ▸ Skill Script → LLM exec 调用（④ 层触发，⑤ 层执行）   │
└─────────────────────────────────────────────────────────┘
```

> **层级关系一句话：Plugin 在 ② 层注册系统能力，Skill 在 ③④ 层扩展 LLM 认知。两者在不同层级各司其职。**

---

## 三、Why：为什么需要两层？

### 仅 Plugin 不够

Plugin 注册了 tool，但 **LLM 只能看到 tool 的 JSON Schema**（参数名 + 类型）。Schema 无法表达：
- **什么时候触发**（用户说"帮我写个飞书文档"时）
- **action 组合策略**（先 read → 检查 block_types → list_blocks）
- **业务约束**（"Markdown 表格不支持，要用 create_table"）
- **错误恢复流程**（后端服务不可用时的 fallback 路径）

### 仅 Skill 不够

Skill 能教 LLM"怎么想、怎么做"，但 **Skill 无法**：
- 注册系统级 provider / channel（需要代码执行环境）
- 维护长连接（WebSocket / Webhook）
- 处理 OAuth 鉴权流程
- 提供 RPC 方法给系统
- 运行常驻后台服务

---

## 四、核心属性对比

| 维度 | Plugin | Skill |
|------|--------|-------|
| **本质** | 代码模块（TypeScript） | 提示词文档（Markdown）+ 可选脚本（`scripts/`） |
| **代码在哪跑** | Gateway Node.js 进程内 | LLM 通过 `exec` tool 间接调用脚本 |
| **加载时机** | Gateway 启动时加载 `index.ts` | 会话中按需注入 SKILL.md |
| **注册什么** | provider / channel / tool / hook / service | 无系统注册（Skill 不向系统注入能力） |
| **生命周期** | 系统级，Gateway 常驻 | 会话级，上下文窗口内 |
| **治理方式** | `plugins.allow/deny/entries`，Gateway 重启生效 | 跟随 Plugin 启停，或 workspace 独立管理 |
| **安全模型** | sandbox 有限，需信任（`plugins.allow` 白名单） | 脚本 + 提示词都可让 LLM 执行命令（供应链风险） |
| **分发方式** | npm `@openclaw/*`、本地路径、tarball / zip | 跟随 Plugin、ClawHub 或 workspace 独立 |

---

## 五、启动时 vs 运行时（生命周期深度解析）

### 启动时（Gateway 启动）

Gateway 启动时按 [Discovery 优先级](https://docs.openclaw.ai/tools/plugin#discovery-&-precedence) 依次扫描 plugin：

```
1. plugins.load.paths（配置指定的路径）
2. <workspace>/.openclaw/extensions/*
3. ~/.openclaw/extensions/*
4. <openclaw>/extensions/*（内置 bundled）
```

**对每个 plugin 执行**：

| 步骤 | 做什么 | 涉及文件 |
|------|--------|----------|
| ① 发现 | 扫描目录，找到入口文件（`index.ts` 或独立 `.ts`） | - |
| ② 安全检查 | 禁止 symlink 逃逸、world-writable、owner 不匹配 | - |
| ③ 准入检查 | 检查 `plugins.allow/deny`，未在白名单则拒绝 | `openclaw.json` |
| ④ Manifest 验证 | 读取并校验 `openclaw.plugin.json`（id、configSchema） | `openclaw.plugin.json` |
| ⑤ Config 验证 | 用 manifest 的 JSON Schema 校验 `plugins.entries.<id>.config` | `openclaw.json` |
| ⑥ 执行 register | 加载 `index.ts`，调用 `register(api)` 注册各种能力 | `index.ts` |
| ⑦ Skill 发现 | 如果 manifest 有 `"skills": [...]`，记录 skill 目录路径 | `skills/*/SKILL.md` |
| ⑧ 启动服务 | 如果注册了 `registerService`，调用 `start()` | `index.ts` |

**注意**：Skill 在启动时**只被发现，不被加载**。SKILL.md 的内容要等到会话运行时才注入 LLM。

### 运行时（一次会话调用）

```
用户消息 → Gateway 收到
       ↓
┌─── Plugin 层（代码执行）───────────────────────────┐
│  Channel plugin 负责收消息、发消息                    │
│  Provider plugin 负责路由到正确的模型 + 鉴权           │
└──────────────────────────────────────────────────┘
       ↓
┌─── Skill 层（提示词注入）──────────────────────────┐
│  来源 1：Plugin 携带的 skill（manifest "skills" 声明）│
│  来源 2：独立 skill（workspace skills/ 目录）         │
│  命中 → SKILL.md 内容注入 LLM system prompt          │
│  未命中 → 不加载，不占上下文                          │
└──────────────────────────────────────────────────┘
       ↓
┌─── LLM 推理（决策结果有四种可能）─────────────────┐
└──────────────────────────────────────────────────┘
       ↓
  ┌────────┬────────────┬────────────┐
  ↓        ↓            ↓            ↓
路径A    路径B        路径C        路径D

Plugin   系统内置     独立 Skill    直接回复
注册的   Tool         驱动的
Tool                  Tool 调用

feishu   read/write   Skill 教 LLM  纯文本，
_doc     exec         调用系统 tool  无 tool
voice    web_fetch    （如执行脚本   call
_call    sessions     部署流程等）
         _spawn

  ↓        ↓            ↓            ↓
Plugin   系统内核     系统内核       无代码
代码     执行，       执行，         执行
执行     Plugin       Plugin
         不参与       不参与
```

**四条路径说明**：

| 路径 | 谁提供 tool | 谁执行 | 例子 |
|------|-----------|--------|------|
| **A. Plugin Tool** | Plugin `registerTool` | Plugin 代码 | `feishu_doc`、`voice_call` |
| **B. 系统内置 Tool** | 系统自带 | 系统内核 | `read`、`write`、`exec`、`web_fetch` |
| **C. 独立 Skill 驱动** | 系统自带 tool + 独立 Skill 指引 | 系统内核（Skill 只影响决策） | workspace 里的 deploy skill 教 LLM 用 `exec` 跑脚本 |
| **D. 直接回复** | 无 | 无 | LLM 直接生成文本回复，不调用任何 tool |

### 不同 Plugin 类型的 Startup vs Runtime

| 类型 | 启动时做什么 | 运行时做什么 | Skill 参与？ |
|------|------------|------------|-------------|
| **Channel**（discord） | `registerChannel` → 建立 WebSocket 连接 | 收消息 → 转给 agent；agent 回复 → 发消息 | ❌ 不需要 |
| **Provider auth**（minimax-portal-auth） | `registerProvider` → 注册 OAuth 流程 | CLI `models auth login` 时执行鉴权；推理时提供 credential | ❌ 不需要 |
| **Tool-only**（diffs） | `registerTool` → 注册 tool schema | LLM 发起 tool call → Plugin 代码执行 | ❌ Schema 足够 |
| **Tool + Skill**（feishu） | `registerChannel` + `registerTool` × 4 | Skill 注入 → LLM 按指引发起 tool call → Plugin 执行 | ✅ 需要 |
| **Runtime + Skill**（acpx） | `registerService`（ACP backend）+ `registerTool` | Skill 注入路由决策 → LLM `sessions_spawn` → Plugin 管理进程 | ✅ 需要 |
| **基础设施**（memory-core） | `registerTool`（内部 tool） | 系统自动调用（auto-recall/capture），LLM 不直接决策 | ❌ 系统自动 |

### 两个具体运行时流程

#### 例：feishu Plugin + Skill 的运行时

```
1. 用户在飞书群发消息："把会议纪要写到这个文档里 https://xxx.feishu.cn/docx/ABC123"
       ↓
2. [Plugin·Channel] feishu channel 收到消息，提交给 agent
       ↓
3. [Skill·注入] 系统匹配到 feishu-doc skill（用户提到飞书文档链接）
   → SKILL.md 注入 LLM 上下文（参数示例、workflow、注意事项）
       ↓
4. [LLM·决策] LLM 读 Skill 后知道：
   - 先用 action: "read" 读现有内容
   - 再用 action: "write" 写入新内容
   - 不能用 Markdown 表格，要用 create_table
       ↓
5. [LLM·tool call] → feishu_doc({ action: "read", doc_token: "ABC123" })
       ↓
6. [Plugin·执行] feishu plugin 代码调用飞书 API，返回文档内容
       ↓
7. [LLM·tool call] → feishu_doc({ action: "write", doc_token: "ABC123", content: "..." })
       ↓
8. [Plugin·执行] feishu plugin 代码写入飞书文档
       ↓
9. [Plugin·Channel] feishu channel 将结果发回飞书群
```

#### 例：acpx Plugin + Skill 的运行时

```
1. 用户说："帮我用 codex 在 /home/zk/myproject 里修个 bug"
       ↓
2. [Skill·注入] 系统匹配到 acp-router skill（用户提到 codex）
   → SKILL.md 注入 LLM 上下文（意图检测 + 模式选择 + agentId 映射）
       ↓
3. [LLM·决策] LLM 读 Skill 后知道：
   - 这是 ACP harness 请求 → 用 sessions_spawn
   - agentId = "codex"
   - runtime = "acp", thread = true
       ↓
4. [LLM·tool call] → sessions_spawn({ task: "修复 bug", runtime: "acp", agentId: "codex", thread: true })
       ↓
5. [Plugin·执行] acpx plugin 启动 acpx 进程，创建 codex session
       ↓
6. [Plugin·服务] acpx 后台服务管理 session 生命周期，返回结果
```

---

## 六、真实例子解析

### A. 不带 Skill 的 Plugin（纯代码能力）

大量 plugin **不需要 skill**——当 tool schema 本身足够清晰、或 plugin 不暴露 agent tool 时，不需要额外教 LLM。

#### A1. Channel-only：discord

最常见的模式。Plugin 只注册消息通道，无 tool、无 skill。

```json
{
  "id": "discord",
  "channels": ["discord"],
  "configSchema": { "type": "object", "additionalProperties": false, "properties": {} }
}
```

**Why 不需要 Skill**：Channel 的收发消息逻辑由 Gateway 统一处理，LLM 不需要知道"怎么连 Discord"。同类：`telegram`、`slack`、`irc`、`matrix`、`line`、`msteams`、`whatsapp` 等。

#### A2. Provider-auth-only：minimax-portal-auth

Plugin 只注册模型 provider 的 OAuth 鉴权流程。

```json
{
  "id": "minimax-portal-auth",
  "providers": ["minimax-portal"],
  "configSchema": { "type": "object", "additionalProperties": false, "properties": {} }
}
```

**Why 不需要 Skill**：鉴权是系统级行为（`openclaw models auth login --provider minimax-portal`），LLM 不参与。同类：`google-gemini-cli-auth`、`qwen-portal-auth`、`copilot-proxy`。

#### A3. Tool-only（Schema 足够清晰）：diffs

Plugin 注册 agent tool（diff 查看器），但 tool 的 JSON Schema 已经足够 LLM 理解如何使用。

```json
{
  "id": "diffs",
  "name": "Diffs",
  "description": "Read-only diff viewer and image renderer for agents.",
  "configSchema": { ... /* 详细的 defaults 配置 */ }
}
```

**Why 不需要 Skill**：`diffs` tool 的 schema 参数（文件路径、layout、theme 等）含义直白，LLM 无需额外指导。同类：`llm-task`、`lobster`。

#### A4. 基础设施类：memory-core

Plugin 提供系统内部能力（内存搜索），不直接暴露给 LLM 决策。

```json
{
  "id": "memory-core",
  "kind": "memory",
  "configSchema": { "type": "object", "additionalProperties": false, "properties": {} }
}
```

**Why 不需要 Skill**：memory 插件通过 `plugins.slots.memory` 自动激活，由系统内部调用，LLM 不需要学习"怎么用 memory"。同类：`memory-lancedb`、`diagnostics-otel`。

#### 小结：何时 Plugin 不需要 Skill

| 场景 | 原因 |
|------|------|
| Channel 插件 | 收发消息由 Gateway 统一，LLM 无需感知 |
| Provider auth 插件 | 鉴权是 CLI/系统级行为 |
| Tool schema 足够清晰 | LLM 从参数名+类型就能正确使用 |
| 系统内部能力 | 不需要 LLM 决策，系统自动调用 |

---

### B. 带 Skill 的 Plugin（能力 + 使用手册）

### B1. acpx — Plugin + 1 Skill（最精简）

| 层 | 做什么 |
|----|--------|
| **Plugin** (`index.ts`) | 注册 ACP runtime backend，管理 acpx 进程，提供 `sessions_spawn` tool |
| **Skill** (`acp-router/SKILL.md`) | 教 LLM：意图检测 → 模式选择（ACP runtime vs 直接 acpx）→ AgentId 映射 → 错误恢复策略 |

```
acpx/
├── openclaw.plugin.json     ← "skills": ["./skills"]
├── index.ts                 ← registerService / registerTool
└── skills/acp-router/
    └── SKILL.md             ← 217 行：路由决策 + 命令模板 + fallback
```

**Why 需要 Skill**：`sessions_spawn` 的 JSON Schema 只能描述参数，但"什么时候用 ACP 而不是 subagent""acpx 不可用时怎么自动修复"这些决策逻辑只能通过 Skill 传达。

---

### B2. feishu — Channel Plugin + 4 Skills（按功能拆分）

| 层 | 做什么 |
|----|--------|
| **Plugin** (`index.ts`) | `registerChannel`（飞书 bot）+ 注册 `feishu_doc` / `feishu_drive` / `feishu_wiki` / `feishu_perm` tools |
| **4 Skills** | 每个 skill 教 LLM 使用一个 tool，含参数示例、workflow、注意事项 |

```
feishu/
├── openclaw.plugin.json     ← "channels": ["feishu"], "skills": ["./skills"]
├── index.ts
└── skills/
    ├── feishu-doc/SKILL.md       ← 12 个 action，含 JSON 示例 + 读写 workflow
    ├── feishu-drive/SKILL.md     ← 云盘操作
    ├── feishu-perm/SKILL.md      ← 权限管理
    └── feishu-wiki/SKILL.md      ← 知识库操作
```

**Why 拆分 4 个 Skill**：飞书 API 复杂（docx block 模型、wiki 与 doc 的关联、权限体系），单个 SKILL.md 会过长。按功能拆分后，LLM 只加载需要的 skill，节省上下文窗口。

---

## 七、Plugin 选型决策指南

| 你要做什么 | 用什么 | Why |
|------------|--------|-----|
| 接入内部模型 API | **Plugin**（`registerProvider`） | 需要代码：HTTP 请求、鉴权、重试、限流 |
| 接入新的聊天平台 | **Plugin**（`registerChannel`） | 需要 WebSocket/Webhook 长连接 |
| 给 LLM 添加新工具 | **Plugin**（`registerTool`） | tool 的执行逻辑需要代码 |
| 教 LLM 正确使用已有工具 | **Skill** | 提示词指引 + 可选脚本辅助 |
| 让 LLM 能跑自定义脚本 | **Skill**（带 `scripts/`） | SKILL.md 教 LLM 何时跑、怎么跑 |
| 定义多 agent 工作流 | **Skill** | 通过 prompt 定义 VM 语义（如 prose） |
| 工具 + 使用手册一起出 | **Plugin 带 Skill** | Plugin 注册 tool + Skill 教 LLM 用 |

---

## 八、安全提示（来自官方 + 社区）

### Plugin 安全
- 用 `plugins.allow` 白名单控制加载
- 路径安全检查：禁止 symlink 逃逸、world-writable 目录、owner 不匹配
- 只安装信任来源的 plugin

### Skill 安全

> **官方原文**："Treat third-party skills as untrusted code. Read them before enabling." — [docs.openclaw.ai/tools/skills](https://docs.openclaw.ai/tools/skills#security-notes)

- **Skill 不是无害的 Markdown**——它可以指导 LLM 执行系统命令、读写文件、触发工作流
- `skills.entries.*.env` 和 `skills.entries.*.apiKey` 会注入 secrets 到宿主进程（不是 sandbox）
- 社区讨论 ClawHub 供应链攻击风险：恶意 skill 可让 LLM 执行任意命令
- 对待 skill 要**像对待基础设施代码一样审慎**
- 对于不受信任的输入，官方建议使用 [Sandboxing](https://docs.openclaw.ai/gateway/sandboxing)

---

## 九、一句话总结（TL;DR）

- **Plugin** = **系统层扩展**（代码跑在 Gateway 进程，注册为系统的一部分）
- **Skill** = **认知层扩展**（提示词 + 可选脚本，在 Agent Runtime 层注入 LLM 上下文）

两层扩展的是**不同层级**：Plugin 给系统装新能力，Skill 教 LLM 怎么用这些能力（或直接带脚本让 LLM 跑）。

### 三句口径（便于讲解）

1. **Plugin = 系统能力 + 代码执行**（启动时加载注册；运行时在 Gateway 进程里承接 tool call）
2. **Skill = 认知指引 + 可选脚本**（提示词教模型决策；scripts/ 里的脚本由 LLM 通过 exec 调用）
3. **Plugin 带 Skill = 全屋定制**（既提供系统级工具，又教会模型怎么用——最完整的模式）

