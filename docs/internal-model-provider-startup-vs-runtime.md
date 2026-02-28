# 内部模型接入 OpenClaw：启动时 vs 运行时（整理稿）

> 背景：领导要求对“内部模型接入 OpenClaw 为什么要用 Plugin”做两段分析：启动时（startup）与运行时（runtime）。
> 目标：用 OpenClaw 官方机制来解释，而不是靠类比。

---

## 一句话结论
内部模型要成为 OpenClaw 的一等公民（可被选择为默认模型、可统一鉴权、可审计/可运维），应通过 **Provider/Auth Plugin** 接入：
- **启动时**完成“发现 + 严格校验 + 注册 provider/auth”
- **运行时**完成“每次调用的执行质量（鉴权/超时/重试/限流/观测）”

Skill 的上限是“会话内通过脚本临时调用”，无法扩展 OpenClaw 的系统模型层。

---

## 1) 启动时（Startup）：把内部模型接入系统模型层
启动时关注：OpenClaw 能否“认识”你的内部模型，以及能否把接入纳入系统治理。

### 1.1 Plugin discovery（发现/加载入口）
Gateway 启动时会按官方 precedence 扫描插件来源（如 `plugins.load.paths`、workspace/global extensions、bundled 等）。

这一步决定：
- 插件是否能被找到
- 若多个来源有同 id，哪个生效

### 1.2 Manifest + Schema validation（严格校验，且不执行插件代码）
每个插件必须提供 `openclaw.plugin.json`，并内嵌 `configSchema`。
OpenClaw 在启动/配置校验阶段使用 manifest + JSON Schema 进行严格验证，**不会为了校验去执行插件代码**。

这一步的价值：
- 把错误前置到启动期（配置错直接 fail fast）
- 避免运行期才发现“参数缺失/类型错误/未知字段”等问题

### 1.3 Registration（注册 provider/auth，成为一等公民）
通过 Provider/Auth plugin，在 register 阶段调用类似 `api.registerProvider(...)`，把：
- provider id（内部供应商）
- auth methods（OAuth / API key / device code 等）
- 产出的 auth profiles（credential 写入）

纳入 OpenClaw。

这一步的结果是：
- OpenClaw 支持 `openclaw models auth login --provider <id>`
- 内部模型可以出现在“可选模型/默认模型”的系统配置里
- 鉴权与配置变成系统级能力，而不是会话内脚本

> 启动时结论：**Plugin 让内部模型进入 OpenClaw 的“系统模型层”**（discoverable、schema-validated、可配置、可登录）。

---

## 2) 运行时（Runtime）：每一次调用怎么可靠可控
运行时关注：一次具体模型调用是否稳定、可观测、可治理。

### 2.1 Dispatch：从“选择模型”到“实际调用实现”
当 agent 在某次请求中选择内部模型，OpenClaw 会走 provider 实现路径执行请求。

### 2.2 Execution quality：可靠性与治理在运行时落地
Provider/Auth plugin（以及其内部 HTTP client/中间件）通常需要承担：
- token 获取与刷新（过期处理）
- 超时/重试策略
- 限流/退避（保护内部推理服务）
- 失败分类与降级（切备、返回可解释错误）
- 观测：日志/指标/审计（谁调用了哪个模型、耗时、失败原因）

> 运行时结论：**Plugin 决定每一次调用的执行质量**（稳定性与可观测）。

---

## 3) 为什么 Skill 不够（明确上限）
Skill 能做的通常是：
- 在某个会话里编排：`exec` 跑脚本/HTTP 请求去调用内部模型

但 Skill 做不到：
- 注册 provider（让 OpenClaw “认识”一种新模型供应商）
- 把鉴权做成系统级登录流程（profiles/credentials）
- 把模型选择/默认模型配置纳入 OpenClaw 的模型体系
- 在网关层统一做校验/限流/审计（只能靠脚本自律）

因此：Skill 方案更像“会话级临时代理”；Plugin 方案才是“系统级接入”。

---

## 4) 推荐落地路线（最实用）
1. **先用 skill + 脚本 PoC**验证业务价值（快）
2. 把内部模型接入升级为 **Provider/Auth plugin**（把鉴权/路由/校验/观测收敛到网关）
3. 再用 skills 固化不同团队 SOP（输出口径/调用策略/失败兜底）

---

## 参考（官方文档方向）
- Plugins（能力清单、发现顺序、配置规则）
- Plugin manifest（`openclaw.plugin.json` + `configSchema`）
- CLI plugins（install/enable/doctor）
- Provider plugins（model auth）相关章节（在 plugins doc 的 Provider plugins 小节）
