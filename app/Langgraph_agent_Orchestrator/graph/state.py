"""
State definitions for the DevOps self-healing agent graph.

Uses LangGraph's annotated state with explicit overwrite reducers to ensure
clean updates during loop-back transitions.
"""

from typing import TypedDict, Annotated, List


def overwrite(current_value, new_value):
    """
    Simple reducer that replaces the current state value with the new one.
    Used to make field update semantics explicit.
    """
    return new_value


class DevOpsAgentState(TypedDict):
    """
    The strict data contract passed between all graph nodes.

    All fields use Annotated[type, overwrite] to clearly indicate that
    each node returns a full replacement value for the fields it updates.
    """
    incident_id: Annotated[str, overwrite]
    source_system: Annotated[str, overwrite]
    raw_logs: Annotated[str, overwrite]
    incident_context: Annotated[dict, overwrite]
    repository_context: Annotated[dict, overwrite]
    slack_context: Annotated[dict, overwrite]
    sandbox_result: Annotated[dict, overwrite]
    slack_notification: Annotated[dict, overwrite]
    source_modes: Annotated[dict, overwrite]
    target_file: Annotated[str, overwrite]
    commit_author: Annotated[str, overwrite]
    priority_level: Annotated[str, overwrite]
    proposed_patch: Annotated[str, overwrite]
    critic_feedback: Annotated[List[str], overwrite] #was an error - now fixed
    critic_approved: Annotated[bool, overwrite]
    retry_counter: Annotated[int, overwrite]
    is_fixed: Annotated[bool, overwrite]
    final_rca_report: Annotated[str, overwrite]
