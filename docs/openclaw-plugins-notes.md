# OpenClaw 扩展机制（会议演示版）：Plugins / Skills / Tools

> 目标：按 **OpenClaw 官方文档口径**，在会议上把扩展机制讲清楚，并能直接用 CLI + 配置文件演示。

---

## 0. 官方 TL;DR（30 秒开场）
- **Plugin（Extension）**：Gateway 启动时加载的 **小型代码模块**，可扩展 OpenClaw：**commands、tools、Gateway RPC、HTTP handlers、background services、skills** 等（官方原话：“small code module”）。
- **Skill**：AgentSkills 兼容的 skill 文件夹（`SKILL.md` + 指令），用来“教 agent 如何使用 tools”。
- **Tool / Tool call**：Plugin 提供 tool（函数接口）；模型在运行时发起 tool call；Gateway 路由到 plugin 实现并回传结构化结果。

一句话：**Plugin 扩展系统能力面（tool surface + gateway capability），Skill 扩展使用方法（SOP）。**

---

## 1. Plugin 在官方定义里到底能做什么？（能力清单）
根据官方 `docs/tools/plugin.md`，Plugins can register：
- Gateway RPC methods
- Gateway HTTP handlers
- Agent tools
- CLI commands
- Background services
- Optional config validation
- **Skills**（在 manifest 里列出 `skills` 目录）
- **Auto-reply commands**（无需调用模型，直接执行）

> 会议演示建议：优先讲 tool + CLI + background service 三类，领导更容易理解“可交付的系统能力”。

---

## 2. Plugin 的“加载与发现”机制（演示必讲）
官方的 discovery & precedence 顺序（先匹配到的 wins）：

1) **Config paths**
- `plugins.load.paths`（文件或目录）

2) **Workspace extensions**
- `<workspace>/.openclaw/extensions/*.ts`
- `<workspace>/.openclaw/extensions/*/index.ts`

3) **Global extensions**
- `~/.openclaw/extensions/*.ts`
- `~/.openclaw/extensions/*/index.ts`

4) **Bundled extensions**（随 OpenClaw 发货，默认 disabled）
- `<openclaw>/extensions/*`

重要规则：
- 同一个 `id` 若在多个来源出现，**先被发现的版本生效**，后面的被忽略。
- Bundled plugins 需要显式 `plugins.entries.<id>.enabled=true` 或 `openclaw plugins enable <id>` 才会加载。

---

## 3. Plugin manifest（`openclaw.plugin.json`）是硬门槛（安全口径）
官方要求：**每个 plugin root 必须包含 `openclaw.plugin.json`**，并且必须内嵌 JSON Schema。

### 3.1 必填字段（官方）
```json
{
  "id": "voice-call",
  "configSchema": {
    "type": "object",
    "additionalProperties": false,
    "properties": {}
  }
}
```

- `id`：插件唯一标识
- `configSchema`：配置 JSON Schema（即使没有配置也必须提供一个空 schema）

### 3.2 常用可选字段（官方）
- `kind`：用于 **plugin slots**（例如 memory 插件）
- `channels`：本插件注册的 channel ids（影响 `channels.<id>` 的校验）
- `providers`：本插件注册的 provider ids（模型鉴权插件）
- `skills`：要加载的 skill 目录（相对 plugin root）
- `uiHints`：配合 Control UI 渲染更好的配置表单（label/placeholder/sensitive）

关键点（演示时一句话讲清）：
- **配置校验不执行插件代码**：OpenClaw 用 manifest + JSON Schema 做预校验，避免“配置错了只能靠跑起来才发现”。

---

## 4. Plugin 配置模型（官方字段名，便于现场改 JSON 演示）
官方配置形状（节选）：
```json5
{
  plugins: {
    enabled: true,
    allow: ["voice-call"],
    deny: ["untrusted-plugin"],
    load: { paths: ["~/Projects/oss/voice-call-extension"] },
    entries: {
      "voice-call": { enabled: true, config: { provider: "twilio" } },
    },
    slots: {
      memory: "memory-core" // 或 "none" 禁用
    }
  }
}
```

官方强调的严格校验规则（你可以当治理亮点讲）：
- `plugins.entries.* / allow / deny / slots` 引用的 plugin id 必须是 **discoverable**，否则 **直接报错**。
- **Unknown `channels.<id>` keys 是 error**，除非某个 plugin manifest 声明了该 channel id。
- plugin config 用 `openclaw.plugin.json` 的 `configSchema` 严格校验。

---

## 5. Skills 在官方口径里的位置（别把它讲成“随便写提示词”）
官方 `docs/tools/skills.md` 关键点：

### 5.1 Skills 的加载位置与优先级
Skills 来自 3 个来源，冲突时优先级：
- `<workspace>/skills`（最高）
- `~/.openclaw/skills`
- bundled skills（最低）

### 5.2 Plugins + skills（官方机制）
- plugin 可以在 `openclaw.plugin.json` 里列出 `skills` 目录，把技能随插件一起交付。
- 这些 plugin skills 只有在 **plugin enabled** 时加载，并且参与正常的 precedence 规则。

> 演示建议：现场展示“同名 skill 在 workspace 覆盖 bundled”的行为，领导会立刻理解“可定制但可控”。

---

## 6. CLI 演示脚本（会议直接照着敲）
来自官方 `docs/cli/plugins.md`：

```bash
openclaw plugins list
openclaw plugins info <id>
openclaw plugins enable <id>
openclaw plugins disable <id>
openclaw plugins doctor
openclaw plugins install <path-or-spec>
openclaw plugins update <id>
openclaw plugins update --all
```

安装/更新的官方安全口径（会议里可以当加分点）：
- npm 安装是 **registry-only**（拒绝 git/url 规格）
- 依赖安装使用 `npm install --ignore-scripts`（禁用生命周期脚本）
- 建议对 npm 安装使用 `--pin` 固定版本

---

## 7. 官方安全/硬化要点（演示时别讲太虚）
官方在 Plugins 文档里给的 hardening 关键点（可当治理卖点）：
- `plugins.allow` 为空且发现了非 bundled 插件时，会打印 warning，提示你 pin trust。
- OpenClaw 会对候选路径做安全检查并可能拒绝加载，例如：
  - 入口解析出 plugin root 之外（含 symlink/path traversal）
  - plugin root/world-writable
  - ownership 可疑（非当前 uid / 非 root）

结论（领导可理解版）：**插件是 in-process 受信代码，但官方提供了 manifest/schema/allowlist/路径安全检查这一整套护栏。**

---

## 8. 会议 Q&A 备答（按官方机制回答，不靠“类比”）

**Q1：Plugin 和 Skill 最大区别？**
- Plugin 扩展“系统能力面”（tools/commands/http handlers/services/skills shipping）；Skill 是“教 agent 如何使用 tools”的流程层。

**Q2：为什么不用 exec 跑脚本就行？**
- PoC 可以；但 plugin tool 是一等接口：schema 校验、可观测、可审计、可限流、配置受 manifest 约束。

**Q3：Plugin 为什么要 manifest + schema？**
- 官方目的就是：在不执行插件代码的情况下完成配置校验，减少运行时事故面。

---

## 9. 官方参考入口（你演示时可直接打开）
- Plugins：`docs/tools/plugin.md`
- Plugin manifest：`docs/plugins/manifest.md`
- CLI plugins：`docs/cli/plugins.md`
- Skills：`docs/tools/skills.md`
