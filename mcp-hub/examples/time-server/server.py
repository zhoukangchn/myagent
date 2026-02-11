#!/usr/bin/env python3
"""MCP Time Server - 提供时间服务."""
import json
import os
from datetime import datetime, timedelta

import pytz

from mcp_hub.sdk import HubServer


def get_time(args: dict) -> str:
    """获取当前时间."""
    timezone = args.get("timezone", "UTC")
    format_str = args.get("format", "%Y-%m-%d %H:%M:%S")
    
    try:
        tz = pytz.timezone(timezone)
        now = datetime.now(tz)
        return now.strftime(format_str)
    except Exception as e:
        return f"错误: {str(e)}"


def list_timezones(args: dict) -> str:
    """列出可用时区."""
    region = args.get("region", "")
    
    all_zones = pytz.all_timezones
    
    if region:
        zones = [z for z in all_zones if region.lower() in z.lower()]
    else:
        # 返回常用时区
        zones = [
            "UTC",
            "Asia/Shanghai",
            "Asia/Tokyo",
            "Asia/Singapore",
            "Europe/London",
            "Europe/Paris",
            "America/New_York",
            "America/Los_Angeles",
            "Australia/Sydney",
        ]
    
    return json.dumps(zones, indent=2, ensure_ascii=False)


def convert_timezone(args: dict) -> str:
    """转换时区时间."""
    time_str = args.get("time", "")
    from_tz = args.get("from", "UTC")
    to_tz = args.get("to", "UTC")
    format_str = args.get("format", "%Y-%m-%d %H:%M:%S")
    
    try:
        # 解析时间
        if time_str:
            from_zone = pytz.timezone(from_tz)
            naive_time = datetime.strptime(time_str, format_str)
            from_time = from_zone.localize(naive_time)
        else:
            from_time = datetime.now(pytz.timezone(from_tz))
        
        # 转换时区
        to_zone = pytz.timezone(to_tz)
        to_time = from_time.astimezone(to_zone)
        
        result = {
            "original": from_time.strftime(format_str),
            "from_timezone": from_tz,
            "converted": to_time.strftime(format_str),
            "to_timezone": to_tz,
        }
        return json.dumps(result, indent=2, ensure_ascii=False)
    
    except Exception as e:
        return f"错误: {str(e)}"


def get_timestamp(args: dict) -> str:
    """获取 Unix 时间戳."""
    timezone = args.get("timezone", "UTC")
    
    try:
        tz = pytz.timezone(timezone)
        now = datetime.now(tz)
        timestamp = int(now.timestamp())
        return f"{timestamp}"
    except Exception as e:
        return f"错误: {str(e)}"


def timestamp_to_datetime(args: dict) -> str:
    """时间戳转日期时间."""
    timestamp = args.get("timestamp", 0)
    timezone = args.get("timezone", "UTC")
    format_str = args.get("format", "%Y-%m-%d %H:%M:%S")
    
    try:
        tz = pytz.timezone(timezone)
        dt = datetime.fromtimestamp(timestamp, tz)
        return dt.strftime(format_str)
    except Exception as e:
        return f"错误: {str(e)}"


def add_time(args: dict) -> str:
    """时间加减."""
    time_str = args.get("time", "")
    days = args.get("days", 0)
    hours = args.get("hours", 0)
    minutes = args.get("minutes", 0)
    timezone = args.get("timezone", "UTC")
    format_str = args.get("format", "%Y-%m-%d %H:%M:%S")
    
    try:
        tz = pytz.timezone(timezone)
        
        if time_str:
            naive_time = datetime.strptime(time_str, format_str)
            base_time = tz.localize(naive_time)
        else:
            base_time = datetime.now(tz)
        
        delta = timedelta(days=days, hours=hours, minutes=minutes)
        result_time = base_time + delta
        
        return json.dumps({
            "original": base_time.strftime(format_str),
            "delta": f"{days}d {hours}h {minutes}m",
            "result": result_time.strftime(format_str),
        }, indent=2, ensure_ascii=False)
    
    except Exception as e:
        return f"错误: {str(e)}"


def main():
    app = HubServer(
        name="time-server",
        hub_url=os.getenv("MCP_HUB_URL", "http://localhost:8000"),
        version="1.0.0",
        description="时间服务 - 提供时区转换、时间戳转换等功能",
        tags=["time", "timezone", "utility"],
    )
    
    # 注册工具
    app.register_tool(
        name="get_time",
        handler=get_time,
        description="获取当前时间",
        input_schema={
            "type": "object",
            "properties": {
                "timezone": {
                    "type": "string",
                    "description": "时区",
                    "default": "UTC",
                },
                "format": {
                    "type": "string",
                    "description": "时间格式",
                    "default": "%Y-%m-%d %H:%M:%S",
                },
            },
        },
    ).register_tool(
        name="list_timezones",
        handler=list_timezones,
        description="列出可用时区",
        input_schema={
            "type": "object",
            "properties": {
                "region": {
                    "type": "string",
                    "description": "按地区过滤 (如: Asia, Europe)",
                    "default": "",
                },
            },
        },
    ).register_tool(
        name="convert_timezone",
        handler=convert_timezone,
        description="转换时区时间",
        input_schema={
            "type": "object",
            "properties": {
                "time": {
                    "type": "string",
                    "description": "要转换的时间 (空则使用当前时间)",
                    "default": "",
                },
                "from": {
                    "type": "string",
                    "description": "源时区",
                    "default": "UTC",
                },
                "to": {
                    "type": "string",
                    "description": "目标时区",
                    "default": "UTC",
                },
                "format": {
                    "type": "string",
                    "description": "时间格式",
                    "default": "%Y-%m-%d %H:%M:%S",
                },
            },
        },
    ).register_tool(
        name="get_timestamp",
        handler=get_timestamp,
        description="获取 Unix 时间戳",
        input_schema={
            "type": "object",
            "properties": {
                "timezone": {
                    "type": "string",
                    "description": "时区",
                    "default": "UTC",
                },
            },
        },
    ).register_tool(
        name="timestamp_to_datetime",
        handler=timestamp_to_datetime,
        description="时间戳转日期时间",
        input_schema={
            "type": "object",
            "properties": {
                "timestamp": {
                    "type": "integer",
                    "description": "Unix 时间戳",
                },
                "timezone": {
                    "type": "string",
                    "description": "时区",
                    "default": "UTC",
                },
                "format": {
                    "type": "string",
                    "description": "时间格式",
                    "default": "%Y-%m-%d %H:%M:%S",
                },
            },
            "required": ["timestamp"],
        },
    ).register_tool(
        name="add_time",
        handler=add_time,
        description="时间加减",
        input_schema={
            "type": "object",
            "properties": {
                "time": {
                    "type": "string",
                    "description": "基准时间 (空则使用当前时间)",
                    "default": "",
                },
                "days": {
                    "type": "integer",
                    "description": "天数",
                    "default": 0,
                },
                "hours": {
                    "type": "integer",
                    "description": "小时数",
                    "default": 0,
                },
                "minutes": {
                    "type": "integer",
                    "description": "分钟数",
                    "default": 0,
                },
                "timezone": {
                    "type": "string",
                    "description": "时区",
                    "default": "UTC",
                },
            },
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
