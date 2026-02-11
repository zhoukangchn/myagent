#!/usr/bin/env python3
"""MCP File Server - 提供文件操作服务."""
import os
from datetime import datetime
from pathlib import Path

from mcp_hub.sdk import HubServer


def list_files(args: dict) -> str:
    """列出目录中的文件."""
    path = args.get("path", ".")
    recursive = args.get("recursive", False)
    
    try:
        target = Path(path)
        if not target.exists():
            return f"错误: 路径不存在: {path}"
        
        files = []
        pattern = "**/*" if recursive else "*"
        
        for entry in target.glob(pattern):
            stat = entry.stat()
            files.append({
                "name": entry.name,
                "path": str(entry),
                "type": "directory" if entry.is_dir() else "file",
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })
        
        import json
        return json.dumps(files, indent=2, ensure_ascii=False)
    
    except Exception as e:
        return f"错误: {str(e)}"


def read_file(args: dict) -> str:
    """读取文件内容."""
    path = args.get("path", "")
    encoding = args.get("encoding", "utf-8")
    
    try:
        content = Path(path).read_text(encoding=encoding)
        return content
    except Exception as e:
        return f"错误: {str(e)}"


def write_file(args: dict) -> str:
    """写入文件内容."""
    path = args.get("path", "")
    content = args.get("content", "")
    encoding = args.get("encoding", "utf-8")
    
    try:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding=encoding)
        return f"成功写入: {path}"
    except Exception as e:
        return f"错误: {str(e)}"


def get_file_info(args: dict) -> str:
    """获取文件详细信息."""
    path = args.get("path", "")
    
    try:
        target = Path(path)
        if not target.exists():
            return f"错误: 文件不存在: {path}"
        
        stat = target.stat()
        import json
        return json.dumps({
            "name": target.name,
            "path": str(target.absolute()),
            "type": "directory" if target.is_dir() else "file",
            "size": stat.st_size,
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "permissions": oct(stat.st_mode)[-3:],
        }, indent=2, ensure_ascii=False)
    
    except Exception as e:
        return f"错误: {str(e)}"


def search_files(args: dict) -> str:
    """搜索文件."""
    path = args.get("path", ".")
    pattern = args.get("pattern", "*")
    
    try:
        target = Path(path)
        matches = list(target.rglob(pattern))
        
        import json
        return json.dumps(
            [{"name": m.name, "path": str(m)} for m in matches],
            indent=2,
            ensure_ascii=False,
        )
    except Exception as e:
        return f"错误: {str(e)}"


def main():
    app = HubServer(
        name="file-server",
        hub_url=os.getenv("MCP_HUB_URL", "http://localhost:8000"),
        version="1.0.0",
        description="文件操作服务 - 提供文件读写、搜索等功能",
        tags=["file", "filesystem", "utility"],
    )
    
    # 注册工具
    app.register_tool(
        name="list_files",
        handler=list_files,
        description="列出目录中的文件和子目录",
        input_schema={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "要列出的目录路径",
                    "default": ".",
                },
                "recursive": {
                    "type": "boolean",
                    "description": "是否递归列出子目录",
                    "default": False,
                },
            },
        },
    ).register_tool(
        name="read_file",
        handler=read_file,
        description="读取文件内容",
        input_schema={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "文件路径",
                },
                "encoding": {
                    "type": "string",
                    "description": "文件编码",
                    "default": "utf-8",
                },
            },
            "required": ["path"],
        },
    ).register_tool(
        name="write_file",
        handler=write_file,
        description="写入文件内容",
        input_schema={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "文件路径",
                },
                "content": {
                    "type": "string",
                    "description": "文件内容",
                },
                "encoding": {
                    "type": "string",
                    "description": "文件编码",
                    "default": "utf-8",
                },
            },
            "required": ["path", "content"],
        },
    ).register_tool(
        name="get_file_info",
        handler=get_file_info,
        description="获取文件详细信息",
        input_schema={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "文件路径",
                },
            },
            "required": ["path"],
        },
    ).register_tool(
        name="search_files",
        handler=search_files,
        description="搜索文件",
        input_schema={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "搜索起始目录",
                    "default": ".",
                },
                "pattern": {
                    "type": "string",
                    "description": "搜索模式 (支持通配符)",
                    "default": "*",
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
