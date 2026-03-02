# Plugin vs Skill 速查

> Plugin 和 Skill 是 OpenClaw 的两种扩展机制，分处不同层级、不同时机加载。

---

## 一、本质区别

| | Plugin | Skill |
|---|---|---|
| **是什么** | TypeScript 代码模块 | Markdown 提示词 + 可选脚本 |
| **跑在哪** | Gateway 进程内 | 注入 LLM 上下文 |
| **干什么** | 注册系统能力（provider / channel / tool / hook / service） | 教 LLM 怎么用这些能力 |
| **生命周期** | 系统级，常驻 | 会话级，按需加载 |

**一句话**：Plugin 给系统装能力，Skill 教模型用能力。

---

## 二、层级关系

```
┌──────────────────────────────────────────┐
│              ① 用户层                     │
│  消息入口（Telegram / CLI / Web …）       │
└──────────────────┬───────────────────────┘
                   ↓
┌──────────────────────────────────────────┐
│  ② Gateway 控制面（系统层）  ← Plugin 在这│
│                                          │
│  Channel  — 消息通道（WebSocket/Webhook） │
│  Provider — 模型路由 + OAuth 鉴权         │
│  Tool     — 注册 agent tool（代码实现）   │
│  Hook / Service / RPC / CLI              │
│                                          │
│  【Plugin 代码跑在 Gateway Node.js 进程】 │
└──────────────────┬───────────────────────┘
                   ↓
┌──────────────────────────────────────────┐
│  ③ Agent Runtime（运行时层） ← Skill 在这 │
│                                          │
│  组装上下文（session history + memory）    │
│  匹配激活条件 → 注入 SKILL.md 到 LLM     │
│  调用 LLM 推理 → 接收 tool call          │
└──────────────────┬───────────────────────┘
                   ↓
┌──────────────────────────────────────────┐
│  ④ LLM 认知层                            │
│                                          │
│  LLM 结合 Skill 提示词 + tool schema 决策 │
│  输出：tool call 或 直接文本回复           │
└──────────────────┬───────────────────────┘
                   ↓
┌──────────────────────────────────────────┐
│  ⑤ 执行层                                │
│                                          │
│  Plugin Tool → Plugin 代码执行（② 层）    │
│  系统 Tool   → 系统内核（read/write/exec）│
│  Skill 脚本  → LLM 通过 exec 调用        │
└──────────────────────────────────────────┘
```

> **核心**：Plugin 在 ② 层注册系统能力，Skill 在 ③④ 层扩展 LLM 认知。两者在不同层级各司其职。

### 为什么需要两层？

**仅 Plugin 不够** — Plugin 注册了 tool，但 LLM 只能看到 JSON Schema（参数名 + 类型），无法表达：
- 什么时候该触发这个 tool
- 多个 action 的组合顺序（先 read → 再 write）
- 业务约束（如「飞书不支持 Markdown 表格」）
- 出错时的恢复流程

**仅 Skill 不够** — Skill 能教 LLM 怎么想，但无法：
- 注册系统级 provider / channel
- 维护长连接（WebSocket / Webhook）
- 处理 OAuth 鉴权
- 运行常驻后台服务

### 运行时消息流转（以 feishu 为例）

```
用户在飞书群说："把会议纪要写到文档 https://xxx.feishu.cn/docx/ABC123"
  ↓
② [Plugin·Channel]  feishu channel 收到消息，提交给 agent
  ↓
③ [Skill·注入]      匹配到 feishu-doc skill → SKILL.md 注入 LLM
  ↓
④ [LLM·决策]        读 Skill 后知道：先 read 读现有内容，再 write 写入
  ↓
⑤ [Plugin·执行]     feishu_doc tool 调用飞书 API 读写文档
  ↓
② [Plugin·Channel]  feishu channel 将结果发回飞书群
```

---

## 三、启动与加载

### Plugin — 启动时加载

Gateway 启动时，按优先级扫描并加载 plugin：

```
扫描路径（优先级从高到低）：
1. plugins.load.paths       （配置指定）
2. <workspace>/.openclaw/extensions/*
3. ~/.openclaw/extensions/*
4. <openclaw>/extensions/*   （内置）
```

**每个 plugin 的加载流程**：

```
发现入口 → 安全检查 → 准入检查(allow/deny)
    → 校验 manifest → 校验 config
    → 执行 register(api) → 记录 skills 路径
    → 启动 service（如有）
```

关键点：
- Plugin 代码**在 Gateway 启动时执行**，之后常驻
- Plugin 携带的 Skill **只被发现、不被加载**（仅记录路径）

### Skill — 运行时按需注入

用户发消息后，Skill 才参与：

```
用户消息 → 匹配 Skill 激活条件
  命中 → SKILL.md 注入 LLM system prompt
  未命中 → 不加载，不占上下文
```

Skill 来源：
1. Plugin 携带（manifest `"skills"` 字段）
2. workspace 独立 `skills/` 目录

### 不同类型的生命周期对比

**Plugin = 系统级，常驻**：随 Gateway 启动而加载，进程不退出就一直存在。

```
Gateway 启动 ──────────────────────────────────── Gateway 关闭
  │                                                   │
  ├── register(api) 执行                               │
  ├── Channel 连接建立，一直保持 ──────────────────────┤
  ├── Service start()，后台常驻 ───────────────────────┤
  └── Tool schema 注册，随时等待调用 ──────────────────┤
```

**Skill = 会话级，按需加载**：每次会话匹配到才注入，会话结束即释放。

```
            会话1              会话2            会话3
              │                  │                │
  用户提到飞书 → 注入 feishu-doc   │   用户提到飞书 → 注入 feishu-doc
              │  SKILL.md        │                │  SKILL.md
           会话结束 → 释放     没提到 → 不加载    会话结束 → 释放
```

> **对比**：Plugin 是「装好就一直在」，Skill 是「用到才拿出来，用完就收」。

| 类型 | 启动时 | 运行时 | Skill？ |
|------|--------|--------|:-------:|
| **Channel**（discord） | `registerChannel` → 建 WebSocket 连接 | 收消息 → 转 agent；回复 → 发消息 | ❌ |
| **Provider auth**（minimax） | `registerProvider` → 注册 OAuth | 推理时提供 credential | ❌ |
| **Tool-only**（diffs） | `registerTool` → 注册 schema | LLM tool call → Plugin 代码执行 | ❌ |
| **Tool + Skill**（feishu） | `registerChannel` + `registerTool` × N | Skill 注入 → LLM 按指引 tool call → Plugin 执行 | ✅ |
| **Service + Skill**（acpx） | `registerService` + `registerTool` | Skill 注入路由决策 → LLM spawn → Plugin 管理进程 | ✅ |
| **基础设施**（memory-core） | `registerTool`（内部） | 系统自动调用，LLM 不直接决策 | ❌ |

> **规律**：不需要 Skill 的 → LLM 不参与决策，或 schema 足够清晰。需要 Skill 的 → tool 复杂，LLM 需要额外指引才能正确使用。

---

## 四、什么时候需要 Skill？

| 场景 | 只用 Plugin | Plugin + Skill |
|------|:-----------:|:--------------:|
| Channel（discord / telegram） | ✅ | — |
| Provider auth（OAuth 鉴权） | ✅ | — |
| Tool schema 简单直白（diffs） | ✅ | — |
| 基础设施（memory-core） | ✅ | — |
| Tool 复杂，需要 workflow 指引（feishu） | — | ✅ |
| 需要意图路由 / 错误恢复（acpx） | — | ✅ |

**判断标准**：LLM 只看 tool 的 JSON Schema 能不能正确使用？
- **能** → 不需要 Skill
- **不能**（需要知道触发时机 / 操作顺序 / 业务约束 / 错误处理）→ 需要 Skill

---

## 五、典型模式速览

### 纯 Plugin（不带 Skill）
```
discord/
├── openclaw.plugin.json   ← channels: ["discord"]
└── index.ts               ← registerChannel(...)
```

### Plugin + Skill
```
feishu/
├── openclaw.plugin.json   ← skills: ["./skills"]
├── index.ts               ← registerChannel + registerTool × 4
└── skills/
    ├── feishu-doc/SKILL.md
    ├── feishu-drive/SKILL.md
    ├── feishu-perm/SKILL.md
    └── feishu-wiki/SKILL.md
```

### 独立 Skill（无 Plugin）
```
my-skill/
├── SKILL.md               ← 入口（YAML frontmatter + 正文）
└── scripts/               ← 可选，LLM 通过 exec 调用
    └── deploy.sh
```

---

## TL;DR

| | Plugin | Skill |
|---|---|---|
| **层级** | ② Gateway 系统层 | ③ Agent 运行时层 |
| **加载** | 启动时执行代码 | 运行时注入提示词 |
| **作用** | 注册系统能力 | 指导 LLM 决策 |
| **关系** | Plugin 可携带 Skill | Skill 可独立存在 |
