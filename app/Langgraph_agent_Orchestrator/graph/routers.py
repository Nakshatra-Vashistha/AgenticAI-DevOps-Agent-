"""
Routing logic switches for the DevOps self-healing graph.
Handles loop counters and loops limit caps to prevent token drainage.
"""

import logging
from app.Langgraph_agent_Orchestrator.graph.state import DevOpsAgentState

logger = logging.getLogger(__name__)


def route_critic_evaluation(state: DevOpsAgentState) -> str:
    """
    Evaluates the Critic's assessment. Bridges a loop back to the coder 
    or pushes forward to sandbox evaluation.
    
    CRITICAL CEILING: Maximum of 3 rejections allowed before breaking loop.
    """
    # 1. If approved, head straight to compilation testing
    if state.get("critic_approved") is True:
        logger.info("🎨 [ROUTER] Critic approved patch. Routing to Sandbox Coordinator.")
        return "go_to_sandbox"

    # 2. Extract the length of our accumulated feedback history list
    feedback_history = state.get("critic_feedback", [])
    rejection_count = len(feedback_history)

    # 3. Hard ceiling check: If we have hit 3 rejections, force a break
    if rejection_count >= 3:
        logger.warning(
            f"🚨 [ROUTER] CRITICAL CEILING BREACHED: Critic has rejected the patch {rejection_count} times. "
            f"Forcefully breaking loop to protect API limits. Routing to Sandbox for ultimate verification."
        )
        return "go_to_sandbox"

    # 4. Otherwise, let it cycle back for another attempt
    logger.info(
        f"🔄 [ROUTER] Critic rejected patch (Attempt {rejection_count}/3). "
        f"Routing back to Repair Engineer for modifications."
    )
    return "loop_back_to_coder"


def route_sandbox_compilation(state: DevOpsAgentState) -> str:
    """
    Evaluates final execution tracking.
    """
    if state.get("is_fixed") is True:
        logger.info("🏁 [ROUTER] Sandbox reports successful fix or terminal fallback reached. Exiting workflow.")
        return "exit_workflow"

    return "exit_workflow"