"""运行循环子图示例"""

from agent_builder.subgraphs.loop_example import loop_subgraph

if __name__ == "__main__":
    print("=" * 50)
    print("子图内循环示例")
    print("=" * 50)
    print()
    
    result = loop_subgraph.invoke({
        "input_data": "测试数据",
        "iteration": 0,
        "max_iterations": 5,
        "result": "",
        "is_satisfied": False,
    })
    
    print()
    print(f"最终结果: {result['result']}")
    print(f"迭代次数: {result['iteration']}")
