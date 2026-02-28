# OpenClaw 扩展机制（官方口径整理）：Plugins / Skills / Tools

> 目标：按 **OpenClaw 官方文档口径**，把扩展机制讲清楚，并能直接用 CLI + 配置文件复现关键行为。

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

> 建议：优先理解 tool + CLI + background service 三类，最能体现“可交付的系统能力”。

---

## 2. Plugin 的“加载与发现”机制
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

关键点（一句话讲清）：
- **配置校验不执行插件代码**：OpenClaw 用 manifest + JSON Schema 做预校验，避免“配置错了只能靠跑起来才发现”。

---

## 4. Plugin 配置模型（官方字段名，便于改 JSON 复现行为）
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

> 建议：展示“同名 skill 在 workspace 覆盖 bundled”的行为，能很快理解“可定制但可控”。

---

## 6. CLI 复现脚本（直接照着敲）
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

安装/更新的官方安全口径（可当安全加分点）：
- npm 安装是 **registry-only**（拒绝 git/url 规格）
- 依赖安装使用 `npm install --ignore-scripts`（禁用生命周期脚本）
- 建议对 npm 安装使用 `--pin` 固定版本

---

## 7. 复现“启动时 vs 运行时”：以官方 Voice Call 插件为例
> 目标：用一条链路把两类行为区分清楚：
> - **启动时**：manifest/schema 驱动的严格校验（错了 gateway 起不来）
> - **运行时**：tool call 路由到 plugin 实现，plugin 真正执行（用 `provider: "log"` 避免外部依赖）

### 7.1 准备：安装插件（一次性）
```bash
openclaw plugins install @openclaw/voice-call
openclaw plugins list | rg voice-call || true
```

### 7.2 启动时：故意写错配置 → 启动期硬失败
在 `~/.openclaw/openclaw.json` 里设置（示意，字段名按官方插件配置 schema 来）：
```json5
{
  plugins: {
    entries: {
      "voice-call": {
        enabled: true,
        config: {
          provider: "not-a-real-provider" // 故意写错
        }
      }
    }
  }
}
```

然后重启 gateway（任选其一）：
```bash
openclaw gateway restart
# 或 systemd
systemctl --user restart openclaw-gateway.service
```

预期现象（讲解点）：
- Gateway 启动失败/Doctor 报错
- 报错原因指向：`openclaw.plugin.json` 的 `configSchema` 校验没通过

可辅助用：
```bash
openclaw plugins doctor
```

### 7.3 修正为可复现模式：provider=log（不打电话也能跑通运行时）
把配置改为：
```json5
{
  plugins: {
    entries: {
      "voice-call": {
        enabled: true,
        config: {
          provider: "log"
        }
      }
    }
  }
}
```

重启 gateway：
```bash
openclaw gateway restart
```

### 7.4 运行时：触发一次“真正执行”（无外部依赖）
> Voice Call 插件通常会注册：tool / CLI / RPC（具体以 `openclaw plugins info voice-call` 为准）。

现场先看它到底暴露了什么：
```bash
openclaw plugins info voice-call
```

讲解要点：
- **此时 plugin 已加载**（启动时通过 schema 校验）
- 当你触发对应的命令/工具时，才发生运行时执行（即使 provider=log，也会走完整 dispatch 路径）

> 备注：如果你要 100% 可复制的“触发方式”，我们需要你本机 `openclaw plugins info voice-call` 的输出（里面会列出它注册的 CLI command 名称，比如 `openclaw voicecall status` 之类）。

---

## 8. 官方安全/硬化要点（别讲太虚）
官方在 Plugins 文档里给的 hardening 关键点（可当治理卖点）：
- `plugins.allow` 为空且发现了非 bundled 插件时，会打印 warning，提示你 pin trust。
- OpenClaw 会对候选路径做安全检查并可能拒绝加载，例如：
  - 入口解析出 plugin root 之外（含 symlink/path traversal）
  - plugin root/world-writable
  - ownership 可疑（非当前 uid / 非 root）

结论（领导可理解版）：**插件是 in-process 受信代码，但官方提供了 manifest/schema/allowlist/路径安全检查这一整套护栏。**

---

## 9. 常见问题备答（按官方机制回答，不靠“类比”）

**Q1：Plugin 和 Skill 最大区别？**
- Plugin 扩展“系统能力面”（tools/commands/http handlers/services/skills shipping）；Skill 是“教 agent 如何使用 tools”的流程层。

**Q2：为什么不用 exec 跑脚本就行？**
- PoC 可以；但 plugin tool 是一等接口：schema 校验、可观测、可审计、可限流、配置受 manifest 约束。

**Q3：Plugin 为什么要 manifest + schema？**
- 官方目的就是：在不执行插件代码的情况下完成配置校验，减少运行时事故面。

---

## 10. 官方参考入口
- Plugins：`docs/tools/plugin.md`
- Plugin manifest：`docs/plugins/manifest.md`
- CLI plugins：`docs/cli/plugins.md`
- Skills：`docs/tools/skills.md`
