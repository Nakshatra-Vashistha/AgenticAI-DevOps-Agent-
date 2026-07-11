"""
Master graph compilation for the DevOps self-healing pipeline.
"""

from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph

# Absolute imports per requirement
from app.Langgraph_agent_Orchestrator.graph.state import DevOpsAgentState
from app.Langgraph_agent_Orchestrator.graph.nodes import (
    sre_analyst_node,
    repair_engineer_node,
    code_critic_node,
    sandbox_coordinator_node,
)
from app.Langgraph_agent_Orchestrator.graph.routers import route_critic_evaluation, route_sandbox_compilation


def build_workflow() -> CompiledStateGraph:
    """
    Constructs and compiles the state graph.
    Returns a compiled graph instance ready for execution.
    """
    # Initialize the graph with the state contract
    builder = StateGraph(DevOpsAgentState)

    # Register all nodes
    builder.add_node("SRE_Analyst", sre_analyst_node)
    builder.add_node("Repair_Engineer", repair_engineer_node)
    builder.add_node("Code_Critic", code_critic_node)
    builder.add_node("Sandbox_Coordinator", sandbox_coordinator_node)

    # Set entry point
    builder.set_entry_point("SRE_Analyst")

    # Linear transitions
    builder.add_edge("SRE_Analyst", "Repair_Engineer")
    builder.add_edge("Repair_Engineer", "Code_Critic")

    # Conditional edge from Code_Critic
    builder.add_conditional_edges(
        "Code_Critic",
        route_critic_evaluation,
        {
            "go_to_sandbox": "Sandbox_Coordinator",
            "loop_back_to_coder": "Repair_Engineer",
        }
    )

    # Conditional edge from Sandbox_Coordinator
    builder.add_conditional_edges(
        "Sandbox_Coordinator",
        route_sandbox_compilation,
        {
            "exit_workflow": END,
            "loop_back_to_coder": "Repair_Engineer",
        }
    )

    # Compile and return the executable engine
    return builder.compile()


# Export the compiled graph for the runtime application
healing_pipeline_engine = build_workflow()