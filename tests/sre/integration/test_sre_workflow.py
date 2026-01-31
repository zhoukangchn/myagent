"""SRE Multi-Agent 完整流程集成测试

模拟从监控到诊断再到执行的完整闭环。
"""

import pytest
import asyncio
from datetime import datetime
from src.sre.agents.shared.state import SREState, IncidentStatus, Severity
from src.sre.agents.monitor.graph import monitor_agent
from src.sre.agents.diagnoser.graph import diagnoser_agent
from src.sre.agents.executor.graph import executor_agent

@pytest.mark.asyncio
async def test_full_sre_workflow_integration():
    """集成测试：手动链接三个子 Agent 的运行"""
    
    # 1. 准备初始状态（模拟告警触发）
    initial_state = {
        "incident_id": "INT-TEST-999",
        "alert_source": "prometheus",
        "severity": Severity.HIGH,
        "title": "Database Connection Spike",
        "resource_info": {"service": "web-api"},
        "metrics_data": {},
        "log_entries": [],
        "time_context": {},
        "max_age_minutes": 30,
        "status": IncidentStatus.MONITORING
    }
    
    print(f"\n[Step 1] 启动 Monitor Agent (ID: {initial_state['incident_id']})...")
    # 2. 运行 Monitor Agent
    monitor_result = await monitor_agent.ainvoke(initial_state)
    assert "metrics_data" in monitor_result
    assert len(monitor_result["log_entries"]) > 0
    print(f"  - Monitor 收集完成。指标: CPU {monitor_result['metrics_data'].get('cpu_usage')}")

    # 3. 运行 Diagnoser Agent
    # 将 Monitor 的结果包装进 Diagnoser 的输入
    diagnoser_input = {
        "incident_id": monitor_result["incident_id"],
        "monitor_data": monitor_result,
        "knowledge_context": "",
        "iteration": 0,
        "max_iterations": 3,
        "current_hypotheses": [],
        "is_satisfied": False,
        "reflection": ""
    }
    
    print(f"[Step 2] 启动 Diagnoser Agent...")
    diagnoser_result = await diagnoser_agent.ainvoke(diagnoser_input)
    assert len(diagnoser_result["current_hypotheses"]) > 0
    assert diagnoser_result["is_satisfied"] is True
    print(f"  - 诊断完成。首选假设: {diagnoser_result['current_hypotheses'][0]['hypothesis']}")

    # 4. 运行 Executor Agent
    # 准备 Executor 输入
    executor_input = {
        "incident_id": diagnoser_result["incident_id"],
        "diagnosis_report": f"Hypothesis: {diagnoser_result['current_hypotheses'][0]['hypothesis']}",
        "action_plan": [],
        "pending_approval": [],
        "executed_actions": [],
        "requires_human_approval": False,
        "current_action": None
    }
    
    print(f"[Step 3] 启动 Executor Agent...")
    executor_result = await executor_agent.ainvoke(executor_input)
    assert len(executor_result["action_plan"]) > 0
    assert len(executor_result["executed_actions"]) > 0
    assert "[Verification]" in executor_result["diagnosis_report"]
    print(f"  - 修复完成。执行动作: {executor_result['action_plan'][0]['tool_name']}")
    print(f"  - 最终状态确认: {executor_result['executed_actions'][0]['status']}")

    print("\n[SUCCESS] SRE 集成链路全线跑通！🦞")
