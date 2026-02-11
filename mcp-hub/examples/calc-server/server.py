#!/usr/bin/env python3
"""MCP Calc Server - 提供数学计算服务."""
import json
import math
import os
import statistics
from typing import Any

from mcp_hub.sdk import HubServer


def calculate(args: dict) -> str:
    """基础数学计算."""
    operation = args.get("operation")
    a = args.get("a", 0)
    b = args.get("b", 0)
    
    operations = {
        "add": lambda x, y: x + y,
        "subtract": lambda x, y: x - y,
        "multiply": lambda x, y: x * y,
        "divide": lambda x, y: x / y if y != 0 else float("inf"),
        "power": lambda x, y: x ** y,
        "modulo": lambda x, y: x % y,
    }
    
    if operation not in operations:
        return f"错误: 未知运算 '{operation}'"
    
    try:
        result = operations[operation](a, b)
        if result == float("inf"):
            return "错误: 不能除以零"
        return f"结果: {result}"
    except Exception as e:
        return f"错误: {str(e)}"


def advanced_math(args: dict) -> str:
    """高级数学函数."""
    func = args.get("function")
    value = args.get("value", 0)
    
    functions = {
        "sqrt": math.sqrt,
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "log": math.log,
        "log10": math.log10,
        "exp": math.exp,
        "floor": math.floor,
        "ceil": math.ceil,
        "abs": abs,
    }
    
    if func not in functions:
        return f"错误: 未知函数 '{func}'"
    
    try:
        result = functions[func](value)
        return f"{func}({value}) = {result}"
    except Exception as e:
        return f"错误: {str(e)}"


def stats(args: dict) -> str:
    """统计分析."""
    numbers = args.get("numbers", [])
    
    if not numbers:
        return "错误: 请输入数字列表"
    
    try:
        result = {
            "count": len(numbers),
            "sum": sum(numbers),
            "mean": statistics.mean(numbers),
            "median": statistics.median(numbers),
            "min": min(numbers),
            "max": max(numbers),
            "std_dev": statistics.stdev(numbers) if len(numbers) > 1 else 0,
        }
        return json.dumps(result, indent=2, ensure_ascii=False)
    except Exception as e:
        return f"错误: {str(e)}"


def convert_unit(args: dict) -> str:
    """单位转换."""
    value = args.get("value", 0)
    from_unit = args.get("from", "")
    to_unit = args.get("to", "")
    
    # 长度转换
    length_units = {
        "m": 1,
        "km": 1000,
        "cm": 0.01,
        "mm": 0.001,
        "ft": 0.3048,
        "in": 0.0254,
        "mi": 1609.34,
    }
    
    # 重量转换
    weight_units = {
        "kg": 1,
        "g": 0.001,
        "mg": 0.000001,
        "lb": 0.453592,
        "oz": 0.0283495,
    }
    
    # 温度转换
    if from_unit in ["c", "f", "k"] and to_unit in ["c", "f", "k"]:
        if from_unit == to_unit:
            result = value
        elif from_unit == "c":
            result = value * 9/5 + 32 if to_unit == "f" else value + 273.15
        elif from_unit == "f":
            result = (value - 32) * 5/9 if to_unit == "c" else (value - 32) * 5/9 + 273.15
        else:  # k
            result = value - 273.15 if to_unit == "c" else (value - 273.15) * 9/5 + 32
        return f"{value} {from_unit} = {result:.2f} {to_unit}"
    
    # 长度/重量转换
    all_units = {**length_units, **weight_units}
    if from_unit in all_units and to_unit in all_units:
        base_value = value * all_units[from_unit]
        result = base_value / all_units[to_unit]
        return f"{value} {from_unit} = {result:.4f} {to_unit}"
    
    return f"错误: 不支持从 '{from_unit}' 转换到 '{to_unit}'"


def main():
    app = HubServer(
        name="calc-server",
        hub_url=os.getenv("MCP_HUB_URL", "http://localhost:8000"),
        version="1.0.0",
        description="数学计算服务 - 提供基础运算、统计分析和单位转换",
        tags=["math", "calculator", "utility"],
    )
    
    # 注册工具
    app.register_tool(
        name="calculate",
        handler=calculate,
        description="基础数学计算 (加减乘除、幂运算、取模)",
        input_schema={
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["add", "subtract", "multiply", "divide", "power", "modulo"],
                    "description": "运算类型",
                },
                "a": {"type": "number", "description": "第一个操作数"},
                "b": {"type": "number", "description": "第二个操作数"},
            },
            "required": ["operation", "a", "b"],
        },
    ).register_tool(
        name="advanced_math",
        handler=advanced_math,
        description="高级数学函数 (平方根、三角函数、对数等)",
        input_schema={
            "type": "object",
            "properties": {
                "function": {
                    "type": "string",
                    "enum": ["sqrt", "sin", "cos", "tan", "log", "log10", "exp", "floor", "ceil", "abs"],
                    "description": "函数名称",
                },
                "value": {"type": "number", "description": "输入值"},
            },
            "required": ["function", "value"],
        },
    ).register_tool(
        name="stats",
        handler=stats,
        description="统计分析 (均值、中位数、标准差等)",
        input_schema={
            "type": "object",
            "properties": {
                "numbers": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "数字列表",
                },
            },
            "required": ["numbers"],
        },
    ).register_tool(
        name="convert_unit",
        handler=convert_unit,
        description="单位转换 (长度、重量、温度)",
        input_schema={
            "type": "object",
            "properties": {
                "value": {"type": "number", "description": "要转换的值"},
                "from": {"type": "string", "description": "源单位 (m, km, kg, lb, c, f 等)"},
                "to": {"type": "string", "description": "目标单位"},
            },
            "required": ["value", "from", "to"],
        },
    )
    
    # 运行服务
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args()
    
    app.run_sync(port=args.port)


if __name__ == "__main__":
    main()
