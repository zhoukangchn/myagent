"""Monitor Agent 节点逻辑

负责收集指标、分析日志和整理环境上下文。
"""

from typing import Any, Dict
import os
from src.app.core.logging import logger
from src.sre.agents.shared.state import MonitorState

# 集成 Prometheus
try:
    from prometheus_api_client import PrometheusConnect
except ImportError:
    PrometheusConnect = None

async def fetch_metrics_node(state: MonitorState) -> Dict[str, Any]:
    """收集相关指标数据"""
    logger.info(f"[Monitor] 正在为事件 {state['incident_id']} 获取指标...")
    
    prom_url = os.getenv("PROMETHEUS_URL", "http://prometheus:9090")
    metrics = {}

    if PrometheusConnect and os.getenv("PROMETHEUS_URL"):
        try:
            prom = PrometheusConnect(url=prom_url, disable_ssl=True)
            # 示例：获取 CPU 使用率
            cpu_query = '1 - avg(rate(node_cpu_seconds_total{mode="idle"}[5m]))'
            result = prom.custom_query(query=cpu_query)
            if result:
                metrics["cpu_usage"] = float(result[0]["value"][1])
            
            # 示例：获取内存使用率
            mem_query = '1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)'
            result = prom.custom_query(query=mem_query)
            if result:
                metrics["memory_usage"] = float(result[0]["value"][1])
                
            logger.info(f"[Monitor] 成功从 {prom_url} 获取真实指标")
        except Exception as e:
            logger.error(f"[Monitor] 获取 Prometheus 指标失败: {e}")
    
    # 如果没有真实数据或获取失败，提供模拟数据兜底
    if not metrics:
        logger.info("[Monitor] 使用模拟指标数据兜底")
        metrics = {
            "cpu_usage": 0.92,
            "memory_usage": 0.78,
            "request_latency_ms": 450,
            "error_rate": 0.05
        }
        
    return {"metrics_data": metrics}

async def analyze_logs_node(state: MonitorState) -> Dict[str, Any]:
    """分析关联日志"""
    logger.info(f"[Monitor] 正在分析事件 {state['incident_id']} 的关联日志...")
    # TODO: 实现日志聚合与异常检测
    log_summary = "发现多条 'Connection pool exhausted' 错误日志，涉及 web-api 服务。"
    return {"log_entries": [{"level": "ERROR", "message": log_summary}]}

async def gather_context_node(state: MonitorState) -> Dict[str, Any]:
    """整理时间轴和环境上下文"""
    logger.info(f"[Monitor] 正在整理事件 {state['incident_id']} 的环境上下文...")
    # TODO: 获取部署记录、变更记录
    context = {
        "recent_deployments": ["v1.2.3 deployed 15m ago"],
        "infrastructure": "AWS EKS",
        "region": "us-east-1"
    }
    # 更新状态机
    from src.sre.agents.shared.state import IncidentStatus
    return {
        "time_context": context,
        "status": IncidentStatus.DIAGNOSING
    }
