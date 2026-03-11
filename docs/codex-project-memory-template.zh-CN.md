# Codex 项目记忆模板

这份模板用于把“希望 Codex 每次进仓库都优先知道的信息”沉淀到仓库里。
最好的使用方式不是一次写很长，而是随着项目推进持续补充。

## 1. 项目一句话

请用 1 到 3 句话说明：

- 这个仓库的核心目标是什么
- 当前分支在做什么
- 这次迭代最重要的验收标准是什么

示例：

```md
这是一个用于把聊天客户端接到 OpenClaw 的桥接工作区。
当前分支重点是打通 Python SSE Gateway 和 OpenClaw WebSocket 插件之间的双向消息链路。
本轮验收标准是：聊天请求可流式返回，cron/subagent 消息可通过 channel 正常回推。
```

## 2. 先看哪些文件

请列出我进入仓库后应该优先阅读的文件，按顺序写。

建议格式：

```md
1. `AGENTS.md`：协作规则、验证要求、代码风格
2. `README.md`：工作区总览和启动方式
3. `docs/xxx.md`：当前方案设计或联调说明
4. `apps/python-gateway/README.md`：网关接口和运行方式
5. `plugins/ts-openclaw-channel/README.md`：插件行为和环境变量
```

## 3. 仓库结构速记

请只写“真正重要”的目录，不要机械罗列全部文件。

建议格式：

```md
- `apps/python-gateway`：Python 网关服务，负责 SSE / WS / channel callback
- `plugins/ts-openclaw-channel`：OpenClaw 插件，负责反向 WS 和 outbound channel
- `docs/`：联调文档、设计说明、运维指引
- `tests/`：根仓库已有 Agent / SRE 测试
```

## 4. 运行与验证

请写出最常用的启动命令、测试命令、联调命令。
如果是 monorepo，请按子项目拆开写。

建议格式：

```md
### Python Gateway
- 启动：`cd apps/python-gateway && PYTHONPATH=src uvicorn main:app --reload`
- 测试：`cd apps/python-gateway && uv run pytest`

### TS Plugin
- 检查：`cd plugins/ts-openclaw-channel && npm install && npm run check`

### 端到端
- 脚本：`./scripts/smoke.sh`
- 手工验证：发送 chat stream、建立 OpenClaw WS、触发 cron outbound
```

## 5. 关键接口与协议

如果项目依赖接口、事件流、消息格式、签名规则，请简明写清楚。
这一节非常有助于减少我每次重新读代码的成本。

建议至少包含：

- 关键 API 路径
- 必需请求头
- 鉴权或签名方式
- 重要 payload 字段
- SSE / WebSocket / callback 的职责分工

## 6. 当前分支目标

请明确写出：

- 这个分支已经完成了什么
- 还没完成什么
- 哪些地方是临时实现或 stub
- 哪些问题是已知风险

建议格式：

```md
已完成：
- ...

待完成：
- ...

已知风险：
- ...
```

## 7. 改代码时的注意事项

这部分最适合写“踩坑经验”和“隐含约束”。

建议包含：

- 哪些文件改动后必须联调
- 哪些环境变量必须同步更新
- 哪些接口必须保持向后兼容
- 哪些测试虽然慢，但不能省
- 哪些目录只是历史遗留，当前分支不要动

## 8. 希望 Codex 默认怎么工作

如果你希望我以后更贴近你的习惯，可以直接写出来。

示例：

```md
- 默认先读 `AGENTS.md`、顶层 `README.md`、当前分支相关 docs
- 做改动前先说明会动哪些文件
- 优先给“最小可验证改动”，不要一上来大重构
- 回答先说结论，再补原因
- 做完代码后附上实际执行过的验证命令
```

## 9. 任务模板

你也可以给我一个固定的任务描述模板，方便每次开工直接套用。

示例：

```md
任务背景：

目标：

涉及目录：

不允许改动：

验收方式：

额外上下文：
```

## 10. 适合这个仓库的已填充示例

下面是一份基于当前 `feat/sse-ws-openclaw-bridge` 分支的简版示例，可继续补充：

```md
项目一句话：
这是一个桥接工作区，用 Python Gateway 暴露 SSE/HTTP 接口，用 OpenClaw TypeScript 插件建立反向 WebSocket，并承接 cron/subagent 的 channel 推送。

先看文件：
1. `AGENTS.md`
2. `README.md`
3. `docs/sse-bridge-cron-guide.zh-CN.md`
4. `apps/python-gateway/README.md`
5. `plugins/ts-openclaw-channel/README.md`

仓库结构：
- `apps/python-gateway`：FastAPI 网关
- `plugins/ts-openclaw-channel`：OpenClaw channel 插件
- `docs/`：联调文档

关键接口：
- `POST /v1/chat/stream`：聊天客户端走 SSE
- `GET /v1/ws/openclaw`：OpenClaw 插件反向 WS 接入
- `POST /v1/channel/post`：cron/subagent outbound callback

当前分支目标：
- 打通 chat -> gateway -> ws -> openclaw -> stream reply
- 打通 openclaw cron/subagent -> channel delivery -> gateway callback
```

## 推荐落地方式

如果你希望我下次进入仓库就快速进入状态，建议至少做这三件事：

1. 把长期协作规则放在 `AGENTS.md`
2. 把当前分支目标放在 `docs/branch-*.md` 或本文件的已填充版本里
3. 每次启动新任务时，直接告诉我“先看哪几个文件”
