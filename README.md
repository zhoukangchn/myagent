# Agent Builder

> LangGraph 多 Agent 构建框架 - 专注子图嵌套与子循环模式

本项目用于学习和实践 LangGraph 的高级特性：
- **子图 (Subgraph)** - 将复杂逻辑封装为可复用组件
- **子图内循环 (Sub-loop)** - 在子图中实现自包含的迭代逻辑

## 项目结构

```
agent_builder/
├── src/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   └── state.py          # 共享状态定义
│   ├── subgraphs/
│   │   ├── __init__.py
│   │   ├── loop_example.py   # 子图内循环示例
│   │   └── nested_example.py # 嵌套子图示例
│   └── main_graph.py         # 主流程入口
├── tests/
│   └── __init__.py
├── examples/
│   └── __init__.py
├── pyproject.toml
└── README.md
```

## 快速开始

```bash
# 安装依赖
uv sync

# 运行示例
uv run python -m examples.loop_example
```

## 学习目标

1. **基础子图** - 将一组节点封装为独立单元
2. **状态传递** - 主图与子图之间的状态共享
3. **子图循环** - 在子图内部实现 while 循环
4. **条件跳转** - 从子图返回到主图的不同路径

## License

MIT
