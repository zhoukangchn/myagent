"""Diagnoser Agent 节点逻辑

负责查询知识库、分析指标与日志的关联性，并生成根因假设。
"""

from typing import Any, Dict
import os
import httpx
from src.app.core.logging import logger
from src.sre.agents.shared.state import DiagnoserState

async def query_knowledge_node(state: DiagnoserState) -> Dict[str, Any]:
    """通过外部诊断服务获取分析建议"""
    logger.info(f"[Diagnoser] 正在为事件 {state['incident_id']} 调用外部诊断服务...")
    
    service_url = os.getenv("DIAGNOSIS_SERVICE_URL")
    context = ""

    if service_url:
        try:
            async with httpx.AsyncClient() as client:
                # 将当前的监控数据发给外部诊断服务
                payload = {
                    "incident_id": state["incident_id"],
                    "metrics": state["monitor_data"].get("metrics_data"),
                    "logs": state["monitor_data"].get("log_entries")
                }
                response = await client.post(f"{service_url}/analyze", json=payload, timeout=10.0)
                if response.status_code == 200:
                    data = response.json()
                    context = data.get("suggestion", "外部服务未提供具体建议")
                    logger.info(f"[Diagnoser] 成功获取外部诊断建议: {context[:50]}...")
                else:
                    logger.error(f"[Diagnoser] 外部服务返回异常: {response.status_code}")
        except Exception as e:
            logger.error(f"[Diagnoser] 调用外部诊断服务失败: {e}")

    # 如果没有配置 URL 或调用失败，使用本地默认逻辑兜底
    if not context:
        logger.info("[Diagnoser] 使用本地知识库逻辑兜底")
        context = "根据本地记录，'Connection pool exhausted' 通常与数据库连接未正常释放或突发高并发有关。"
    
    return {"knowledge_context": context}

async def analyze_correlation_node(state: DiagnoserState) -> Dict[str, Any]:
    """分析关联性"""
    logger.info(f"[Diagnoser] 正在分析指标与日志的关联性...")
    # TODO: 实现指标趋势与日志异常的时间对齐分析
    analysis = "指标显示 CPU 飙升与 'Connection pool' 错误在时间上完全重合。"
    return {"reflection": analysis}

async def generate_hypothesis_node(state: DiagnoserState) -> Dict[str, Any]:
    """生成根因假设"""
    logger.info(f"[Diagnoser] 正在生成根因假设...")
    # TODO: 使用 LLM 生成多个假设
    hypotheses = [
        {"hypothesis": "数据库连接池配置过小", "confidence": 0.8, "evidence": ["Connection pool exhausted logs"]},
        {"hypothesis": "下游服务响应慢导致连接积压", "confidence": 0.5, "evidence": ["Increased request latency"]}
    ]
    
    from src.sre.agents.shared.state import IncidentStatus
    return {
        "current_hypotheses": hypotheses,
        "is_satisfied": True,
        "status": IncidentStatus.EXECUTING
    }
