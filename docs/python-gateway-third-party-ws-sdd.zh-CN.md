# Python Gateway 第三方 WebSocket 出站接入 SDD

## 1. 文档目的

本文档说明 `feat: add outbound third-party websocket client` 这次改动的设计目标、模块拆分、运行流程和关键约束。

目标读者：

- 维护 `apps/python-gateway` 的开发者
- 需要接入第三方 WebSocket 协议的集成人员
- 需要理解 SSE 与第三方 WS 两条链路如何复用同一套聊天流的开发者

## 2. 背景

在本次改动之前，`python-gateway` 主要提供一条入口链路：

- 客户端通过 `POST /v1/chat/stream` 发起聊天请求
- gateway 将请求转发到 OpenClaw WebSocket
- gateway 以 SSE 的形式将流式结果返回给客户端

该实现的问题是：

- 聊天执行逻辑与 HTTP/SSE 协议耦合
- 如果要支持新的入口协议，需要重复实现一套发送、等待、超时、结束和错误处理逻辑
- gateway 只能被动接收入站请求，不能主动连接外部 WebSocket 服务

## 3. 设计目标

本次改动的目标如下：

- 将聊天执行主流程从 HTTP 路由中抽离，形成可复用的内部事件流
- 在不破坏现有 SSE 行为的前提下，新增第三方 WebSocket 出站接入能力
- 使 gateway 可以主动连接外部 WebSocket 服务，并在同一条 socket 上接收请求、返回流式结果
- 将“内部事件模型”和“外部协议模型”解耦，降低后续接入其他协议的成本

非目标：

- 不修改 OpenClaw 上游协议本身
- 不替换现有 SSE API
- 不引入新的持久化或消息队列组件

## 4. 总体设计

本次改动将系统拆为三层：

1. 聊天执行层
   由 `stream_chat_request()` 统一处理一次聊天请求的完整生命周期。
2. 协议适配层
   由 `ThirdPartyProtocolAdapter` 负责第三方 WS 消息和内部事件之间的双向映射。
3. 连接管理层
   由 `ThirdPartyWsClient` 负责主动建立、维持和重连第三方 WebSocket 连接。

整体上形成两条入口，共用一条核心执行流：

- SSE 入口：HTTP Request -> `stream_chat_request()` -> OpenClaw -> SSE Response
- 第三方 WS 入口：Third-Party WS Message -> `stream_chat_request()` -> OpenClaw -> Third-Party WS Response

## 5. 模块设计

### 5.1 聊天执行层

文件：

- `apps/python-gateway/src/app/services/chat_flow.py`

核心函数：

- `stream_chat_request()`

职责：

- 生成或透传 `request_id`
- 生成或透传 `session_key`
- 输出统一的 `gateway.ack`
- 做会话级并发保护
- 检查 OpenClaw 连接状态
- 向 OpenClaw 发送标准 `user.message`
- 从 bridge 队列中持续读取上游事件
- 处理超时、结束和错误
- 在退出时统一做 stream 注销和 session 释放

设计要点：

- `session_key` 默认规则为 `chat_id:thread_id`
- HTTP 和第三方 WS 两种入口都复用同一套会话串行控制逻辑
- 返回值统一为 `AsyncIterator[dict]`，便于被 SSE 或 WS 适配层消费
- 对 `assistant.error + upstream_empty` 且前面已有输出的场景做兼容收敛，转换为 `assistant.done`

### 5.2 SSE 适配层

文件：

- `apps/python-gateway/src/app/api/routes/chat.py`

职责：

- 接收 `POST /v1/chat/stream`
- 解析请求体为 `ChatStreamRequest`
- 调用 `stream_chat_request()`
- 将内部事件转换为 SSE 事件名称和数据结构

本次改动后，该路由只负责协议适配，不再承载聊天主流程。

### 5.3 第三方协议适配层

文件：

- `apps/python-gateway/src/app/services/third_party_protocol.py`

核心对象：

- `ThirdPartyInboundRequest`
- `ThirdPartyProtocolAdapter`
- `ProtocolError`

职责：

- 解析第三方入站消息
- 校验必要字段
- 构造内部标准 `ChatStreamRequest`
- 将 gateway 内部事件映射为第三方协议事件
- 在协议非法时构造标准错误响应

支持的入站消息类型：

- `chat.message`
- `user.message`

支持的出站消息映射：

- `gateway.ack` -> `chat.ack`
- `assistant.message_start` -> `chat.reply.start`
- `assistant.delta` -> `chat.reply.delta`
- `assistant.done` -> `chat.reply.done`
- `assistant.error` -> `chat.reply.error`
- `tool.event` -> `chat.tool`

设计意义：

- 将第三方协议格式隔离在单一模块中
- 后续若第三方协议字段变化，仅需修改适配层

### 5.4 第三方 WebSocket 客户端

文件：

- `apps/python-gateway/src/app/services/third_party_ws_client.py`

核心类：

- `ThirdPartyWsClient`

职责：

- 根据配置决定是否启用第三方 WS 模式
- 主动连接目标 WebSocket 服务端
- 维持连接、处理断线重连
- 读取每条入站消息并并发处理
- 将内部事件流回写到同一条 WebSocket 连接
- 在 shutdown 时优雅停止后台任务

设计要点：

- 使用 `start()` 和 `close()` 管理后台任务生命周期
- 使用 `_run_forever()` 实现指数退避重连
- 使用 `send_lock` 保证同一连接上的发送串行化
- 每条入站请求独立创建任务处理，避免长回复阻塞后续消息读取

### 5.5 应用装配层

文件：

- `apps/python-gateway/src/app/main.py`

职责：

- 初始化 `settings`
- 初始化全局 `BridgeService`
- 初始化 `ThirdPartyWsClient`
- 将 `stream_chat_request()` 作为 `event_source` 注入第三方 WS client
- 通过 FastAPI `lifespan` 在应用启动和关闭时管理 third-party WS client

这使得第三方 WS 能力成为应用生命周期的一部分，而不是额外的独立进程。

## 6. 运行流程

### 6.1 现有 SSE 流程

1. 客户端调用 `POST /v1/chat/stream`
2. 路由解析请求体并调用 `stream_chat_request()`
3. `stream_chat_request()` 发送 `gateway.ack`
4. gateway 获取 session 锁并校验 OpenClaw 连接
5. gateway 向 OpenClaw 发送 `user.message`
6. gateway 持续读取上游事件
7. 路由层将内部事件转换为 SSE 事件后返回给客户端
8. 请求结束后释放 stream 和 session

### 6.2 第三方 WS 流程

1. 应用启动时，`ThirdPartyWsClient` 根据配置主动连接第三方 WebSocket 服务
2. 第三方服务通过该连接发送一条 `chat.message` 或 `user.message`
3. `ThirdPartyProtocolAdapter.parse_inbound()` 将其转换为 `ThirdPartyInboundRequest`
4. `ThirdPartyWsClient` 调用 `stream_chat_request()`
5. gateway 按既有逻辑向 OpenClaw 发起聊天请求
6. `stream_chat_request()` 持续产出内部事件
7. `ThirdPartyProtocolAdapter.from_gateway_event()` 将内部事件映射为第三方协议事件
8. `ThirdPartyWsClient` 将这些事件按顺序写回同一条 WebSocket

## 7. 配置设计

新增配置项如下：

- `THIRD_PARTY_WS_ENABLED`
- `THIRD_PARTY_WS_URL`
- `THIRD_PARTY_WS_CONNECT_TIMEOUT_SEC`
- `THIRD_PARTY_WS_RECONNECT_MIN_MS`
- `THIRD_PARTY_WS_RECONNECT_MAX_MS`
- `THIRD_PARTY_WS_PING_INTERVAL_SEC`
- `THIRD_PARTY_WS_PING_TIMEOUT_SEC`
- `THIRD_PARTY_WS_HEADERS_JSON`
- `THIRD_PARTY_WS_BEARER_TOKEN`

配置目的：

- 控制功能开关
- 指定第三方 WS 地址
- 控制连接建立超时与保活参数
- 控制断线重连的最小和最大退避时间
- 支持附加自定义 header 或 Bearer Token

## 8. 错误处理与边界条件

系统当前处理的关键边界包括：

- 同一 `session_key` 已有请求在执行时，返回 `session_busy`
- OpenClaw 未连接时，返回 `upstream_unavailable`
- 上游长时间无响应时，返回 `upstream_timeout`
- 第三方消息不是合法 JSON 时，返回 `invalid_json`
- 第三方消息结构不合法或缺字段时，返回 `invalid_message`
- 第三方消息类型不支持时，返回 `unsupported_type`
- 若连接断开，第三方 WS client 自动重试连接

兼容逻辑：

- 若已收到 `assistant.delta`，但后续收到 `assistant.error(code=upstream_empty)`，则将其视为正常结束并输出 `assistant.done`

## 9. 并发与资源管理

### 9.1 会话级并发控制

- 通过 `BridgeService.try_acquire_session()` 保证同一 `session_key` 只有一个活跃请求
- 在请求结束后统一释放 session

### 9.2 连接级并发控制

- 第三方 WebSocket 连接上，多条请求可以并发处理
- 发送时通过 `send_lock` 串行化 `ws.send()`，避免并发写 socket 导致消息交错

### 9.3 生命周期管理

- 应用启动时自动启动第三方 WS client
- 应用关闭时取消后台任务并等待清理完成

## 10. 可测试性

本次改动新增和覆盖的测试重点如下：

- 配置默认值与环境变量覆盖
- 第三方协议解析与映射
- 第三方 WS client 的 roundtrip 行为

测试价值：

- 保证新配置项可正确读取
- 保证第三方协议与内部协议的映射稳定
- 保证在本地 WebSocket server 场景下，消息能从入站到回写完整跑通

## 11. 设计收益

本次设计带来的直接收益如下：

- 将聊天业务流与传输协议解耦
- 为 gateway 增加主动接入外部 WebSocket 生态的能力
- 降低未来扩展新的入口协议的实现成本
- 让现有 SSE 与新增第三方 WS 共用同一套核心逻辑，减少重复代码和行为漂移风险

## 12. 后续可演进方向

可考虑的后续增强包括：

- 为第三方协议增加版本号或能力协商机制
- 增加更细粒度的连接状态指标与监控
- 为第三方 WS client 增加请求级限流和并发上限
- 增加更多端到端集成测试，覆盖异常断线和重连场景

