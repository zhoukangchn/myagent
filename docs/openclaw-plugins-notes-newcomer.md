# OpenClaw 新人速通：Plugin / Skill / Tool call 到底是什么？

> 目标：5 分钟搞懂三个概念，不再混。

---

## 1) 三句口诀（背下来就行）
- **Plugin = 工具箱 + 手**：把外部能力接进来，并且在运行时真的去执行。
- **Skill = 说明书 + 流程**：写进提示词里，教模型怎么用工具箱、怎么兜底、输出长啥样。
- **Tool call = 按按钮**：模型在运行时发起一次结构化函数调用。

一句话：**Plugin 提供“能做什么 + 怎么执行”，Skill 提供“怎么做得对”，Tool call 负责“这次就这么做”。**

---

## 2) 先把词儿说清楚（最少但精确）

### Tool / Tool call
- **Tool**：一个给模型调用的“函数接口”（有参数 schema + 结构化返回）。
- **Tool call**：模型对某个 tool 的一次具体调用（传参 → 得到结果）。

### Skill
Skill 通常包含：
- 步骤（先问什么、再调用哪个工具、怎么判断结束）
- 选工具/填参数的策略
- 失败兜底（重试/换路径/追问用户）
- 输出格式模板（要点/表格/JSON）

关键点：**Skill 不等于能力本身**，它主要改变“模型怎么做”。

### Plugin
Plugin（extension）是 Gateway 启动时加载的模块，它干两件事：
- **启动时**：把 tools 注册出来，并准备好运行环境（鉴权/HTTP client/重试限流/日志/DB 等底座）。
- **运行时**：当模型发出 tool call，OpenClaw 把调用路由到 plugin 的工具实现 → plugin 执行 → 返回结果。

关键点：**真正“干活”发生在运行时的 tool call 之后，不是只在启动时干一票。**

---

## 3) 一条调用链把概念钉死（最重要）

用户：**“帮我查一下上海明天会不会下雨？”**

1. OpenClaw 注入一个“天气 Skill”（告诉模型：需要 city/date、用哪个 tool、失败怎么降级、输出格式）
2. 模型发起 tool call：`get_weather(city="上海", date="明天")`
3. OpenClaw 把这个 tool call 路由给 **Weather plugin** 的实现
4. Plugin 运行时请求天气 API → 返回结构化结果
5. 模型把结果写成中文给用户（是否下雨、温度、建议带伞）

---

## 4) 什么时候用 Skill？什么时候必须上 Plugin？（新人决策表）

### ✅ 先写 Skill 就够（快、便宜、PoC）
- 只是把事情写成 SOP（汇总、报告、抓网页、发通知）
- 能完全用现有工具完成（`web_fetch`/`browser`/`message`/`exec` 等）
- 允许一定不确定性 + 人工兜底

### ✅ 需要 Plugin 的信号（系统能力增量）
- 你要 **新增一个真正的一等 tool**（带 schema，可治理），而不是 `exec + 脚本` 兜一圈
- 你要接入 **新渠道**（新聊天平台）
- 你要 **常驻服务/事件驱动入口**（webhook/队列 consumer/poller）
- 你要做 **系统级模块替换**（例如 memory/检索的实现）
- 你要把 **鉴权/登录** 做成系统级能力（provider/auth）

推荐路线（最不容易踩坑）：**先 Skill 跑通 → 把最核心/最危险的外部集成那段升级成 Plugin tool。**

---

## 5) 新手最常见的 4 个误区
1. **把 plugin 当成“启动时配置文件”**：错，plugin 运行时会执行 tool call。
2. **以为写了 skill 就等于新增能力**：错，skill 主要是“教模型怎么用已有能力”。
3. **用 exec 脚本硬凑一个 tool**：PoC 可以，长期建议做成 plugin tool（有 schema/错误处理/权限边界）。
4. **只讲概念不讲链路**：记住第 3 节那条“天气调用链”，基本就不混了。

---

## 6) 你现在能用的命令（够用版）
- `openclaw plugins list`
- `openclaw plugins info <id>`
- `openclaw plugins enable <id>` / `disable <id>`
- `openclaw plugins doctor`

文档入口（需要再看）：<https://docs.openclaw.ai/cli/plugins>
