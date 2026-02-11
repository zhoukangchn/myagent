# Calc Server

MCP 数学计算服务，提供基础运算、统计分析和单位转换。

## 运行

```bash
# 安装依赖
uv sync

# 运行
MCP_HUB_URL=http://localhost:8000 uv run python server.py
```

## 工具列表

| 工具名 | 功能 |
|--------|------|
| `calculate` | 基础运算 (加减乘除、幂、取模) |
| `advanced_math` | 高级函数 (sqrt, sin, cos, log 等) |
| `stats` | 统计分析 |
| `convert_unit` | 单位转换 |
