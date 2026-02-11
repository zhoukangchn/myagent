# MCP Hub Demo（Client 走 MCP 协议）实施计划

## Summary
构建 Python Hub：控制面 REST 动态注册下游 MCP Server；数据面对 Client 暴露 MCP（initialize/tools/list/tools/call）；Hub 转发到下游 Streamable HTTP MCP。

## Scope
- 管理面 REST: `/api/servers` CRUD
- 数据面 MCP: `/mcp` 三个方法
- 内存存储 + 无鉴权
- 最小管理页

## Acceptance
- MCP client 可走通 initialize -> tools/list -> tools/call
- 可运行时新增/删除下游 server
- 有单元与 API 测试覆盖核心行为
