"""
Node processing functions for the DevOps self-healing graph.
Each node accepts the full state and returns a dictionary of updates.
Fully integrated with the local MCP server for incident, repository, sandbox,
and Slack data boundaries.
"""

import logging
import re
import time
from typing import Dict, Any

from langchain_core.messages import SystemMessage, HumanMessage

from app.Langgraph_agent_Orchestrator.graph.state import DevOpsAgentState
from app.Langgraph_agent_Orchestrator.agents.factory import LLMBrainFactory
from app.Langgraph_agent_Orchestrator.agents.prompts import (
    SRE_ANALYST_PROMPT,
    REPAIR_ENGINEER_PROMPT,
    CODE_CRITIC_PROMPT,
)

from app.The_Tools_Layer.mcp_client import call_mcp_tool

logger = logging.getLogger(__name__)

# Initialize the core LLM once at the module layer
llm = LLMBrainFactory.get_llm()


def _message_content_to_text(content: Any) -> str:
    """Helper to cleanly extract text content from LangChain response wrappers."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                parts.append(str(item.get("text", "")))
            else:
                parts.append(str(item))
        return "".join(parts)
    return str(content)


def sre_analyst_node(state: DevOpsAgentState) -> Dict[str, Any]:
    """
    Triage agent: analyses raw logs and fills initial incident metadata.
    Uses dynamic regex matching first, falling back to LLM processing.
    """
    raw = state.get("raw_logs", "")
    source = state.get("source_system", "github").lower()
    updates: Dict[str, Any] = {}

    try:
        incident_payload = call_mcp_tool(
            "fetch_incident_context",
            {
                "source": source if source in {"github", "datadog", "slack"} else "github",
                "incident_id": state.get("incident_id", "UNKNOWN"),
                "raw_logs": raw,
            },
        )
        updates["incident_context"] = incident_payload.get("context", incident_payload)
        updates["source_modes"] = incident_payload.get("source_modes", {})

        slack_payload = call_mcp_tool(
            "fetch_slack_context",
            {"incident_id": state.get("incident_id", "UNKNOWN")},
        )
        updates["slack_context"] = slack_payload.get("slack_context", {})
        if slack_payload.get("source_modes"):
            updates["source_modes"] = slack_payload["source_modes"]
    except Exception as e:
        logger.error(f"SRE Analyst MCP context fetch failed: {e}", exc_info=True)
        updates["incident_context"] = {"error": str(e)}

    # 1. Dynamic regex sweep to capture ANY file matching .py, .js, or .ts extensions
    file_match = re.search(r"([\w-]+\.py|[\w-]+\/[\w-]+\.js|[\w-]+\.js|[\w-]+\.ts)", raw, re.IGNORECASE)
    
    if file_match:
        updates["target_file"] = file_match.group(1).strip()
        updates["priority_level"] = "🚨 P1 CRITICAL"
        updates["commit_author"] = "git_analyst"
        logger.info(f"SRE Analyst: Dynamically matched culprit file from log trace -> {updates['target_file']}")
        return updates

    incident_context = updates.get("incident_context", {})
    if isinstance(incident_context, dict):
        suggested_file = incident_context.get("file_path") or incident_context.get("target_file")
        if not suggested_file and isinstance(incident_context.get("context"), dict):
            suggested_file = incident_context["context"].get("file_path")
        if suggested_file:
            updates["target_file"] = str(suggested_file).strip()
            updates["priority_level"] = "🚨 P1 CRITICAL"
            updates["commit_author"] = incident_context.get("author", "mcp_context")
            logger.info(f"SRE Analyst: MCP identified culprit file -> {updates['target_file']}")
            return updates

    # 2. Legacy fallback routing check for standard static pipeline paths
    if "ImportModuleError" in raw or "Cannot find module" in raw:
        updates["target_file"] = "config/pipeline-rules.js"
        updates["commit_author"] = "devops_engineer"
        updates["priority_level"] = "🚨 P1 CRITICAL"
        logger.info("SRE Analyst: Detected static import error (fallback) -> targeting pipeline-rules.js")
        return updates

    # 3. Dynamic LLM identification branch if regex misses everything
    try:
        system_msg = SystemMessage(content=SRE_ANALYST_PROMPT)
        user_msg = HumanMessage(
            content=f"Analyse the following crash log and return only a line with:\n"
                    f"TARGET_FILE: <file path>\n"
                    f"PRIORITY: <priority level>\n\n"
                    f"Log:\n{raw}"
        )
        response = llm.invoke([system_msg, user_msg])
        llm_output = _message_content_to_text(response.content).strip()

        target_match = re.search(r"TARGET_FILE:\s*(.+)", llm_output, re.IGNORECASE)
        priority_match = re.search(r"PRIORITY:\s*(.+)", llm_output, re.IGNORECASE)

        updates["target_file"] = target_match.group(1).strip() if target_match else "unknown"
        updates["priority_level"] = priority_match.group(1).strip() if priority_match else "P3 NORMAL"
        updates["commit_author"] = "llm_analyst"

        logger.info(f"SRE Analyst (LLM): target={updates['target_file']}, priority={updates['priority_level']}")
    except Exception as e:
        logger.error(f"SRE Analyst LLM execution failed: {e}", exc_info=True)
        updates["target_file"] = "unknown"
        updates["commit_author"] = "unknown"
        updates["priority_level"] = "P3 NORMAL"

    return updates


def repair_engineer_node(state: DevOpsAgentState) -> Dict[str, Any]:
    """
    Coder agent: Generates a structural code patch.
    Queries the MCP server for repository source code, dependency references,
    and git timelines to prevent silent regression errors.
    """
    # Rate limiter pacing buffer to protect your free tier API quotas
    time.sleep(2)

    raw_logs = state.get("raw_logs", "")
    target_file = state.get("target_file", "unknown")

    if not target_file or target_file == "unknown":
        return {"proposed_patch": "# ERROR: Suspect target file could not be determined."}

    try:
        repository_payload = call_mcp_tool(
            "fetch_repository_context",
            {"suspect_file": target_file},
        )
        code_context = repository_payload.get("repository_context", repository_payload)
    except Exception as e:
        logger.error(f"MCP repository context compilation failed: {e}", exc_info=True)
        code_context = {"error": str(e)}

    # Compile the critique history tracking array to learn from past rejections
    past_failures = state.get("critic_feedback", []) or []
    failure_context = ""
    if past_failures:
        failure_context = "\n⚠️ PAST REJECTED INTERMEDIATE ATTEMPTS (DO NOT REPEAT THESE MODIFICATIONS):\n" + "\n".join(f"- {f}" for f in past_failures)

    # Injecting the historical git timelines cleanly into the engineering context payload
    timeline_str = ""
    if code_context.get("timeline_history"):
        timeline_str = "\n⏳ RECENT GIT REVISION TIMELINE HISTORY (CHECK FOR RECENT REGRESSIONS):\n"
        for commit in code_context["timeline_history"]:
            timeline_str += f"- Commit [{commit['sha']}] by {commit['author']}: '{commit['message']}'\n"
            timeline_str += f"  Changes:\n{commit['code_diff_applied']}\n"

    system_msg = SystemMessage(content=REPAIR_ENGINEER_PROMPT)
    user_msg = HumanMessage(
        content=f"CRASHING LOGGER TRACE:\n{raw_logs}\n\n"
                f"CURRENT SOURCE CODE OF FAILED COMPONENT (`{target_file}`):\n"
                f"{code_context.get('source_code', '// No code found.')}\n\n"
                f"GLOBAL DEPENDENT CHANNELS (Other repository items pointing here):\n"
                f"{code_context.get('global_dependencies', [])}\n"
                f"{timeline_str}"
                f"{failure_context}\n"
                f"Generate an accurate, robust code patch. Return ONLY valid executable code, no markdown fence wrappers."
    )

    try:
        response = llm.invoke([system_msg, user_msg])
        patch = _message_content_to_text(response.content).strip()

        # Sanitize common model markdown fencing anomalies
        patch = re.sub(r"^```\w*\n?", "", patch)
        patch = re.sub(r"\n```$", "", patch)

        return {
            "proposed_patch": patch,
            "repository_context": code_context,
        }
    except Exception as e:
        logger.error(f"Repair Engineer generation loop caught exception: {e}", exc_info=True)
        return {"proposed_patch": f"# ERROR: Exception occurred inside engineering brain: {str(e)}"}


def code_critic_node(state: DevOpsAgentState) -> Dict[str, Any]:
    """
    Reviewer agent: validates the structural alignment of the proposed patch.
    Accumulates feedback items into an incremental list array to power the router's ceiling checks.
    """
    time.sleep(2)

    raw_logs = state.get("raw_logs", "")
    proposed_patch = state.get("proposed_patch", "")
    current_feedback_history = state.get("critic_feedback", []) or []

    system_msg = SystemMessage(content=CODE_CRITIC_PROMPT)
    user_msg = HumanMessage(
        content=f"Original infrastructure log traces:\n{raw_logs}\n\n"
                f"Proposed patch draft snippet:\n{proposed_patch}\n\n"
                f"Verify validation alignment. Respond with 'APPROVED' or 'REJECTED' accompanied by systemic evaluation feedback."
    )

    try:
        response = llm.invoke([system_msg, user_msg])
        verdict = _message_content_to_text(response.content).strip()

        if "APPROVED" in verdict.upper():
            return {"critic_approved": True}
        else:
            # Safely duplicate and append code critique history arrays
            new_history = list(current_feedback_history)
            new_history.append(verdict)
            logger.warning(f"Code Critic: Patch compilation variant rejected. Reason feedback: {verdict}")
            return {
                "critic_approved": False,
                "critic_feedback": new_history
            }
    except Exception as e:
        logger.error(f"Code Critic evaluation phase hit exception: {e}", exc_info=True)
        return {
            "critic_approved": False,
            "critic_feedback": current_feedback_history + [f"System verification timeout failure: {str(e)}"]
        }


def sandbox_coordinator_node(state: DevOpsAgentState) -> Dict[str, Any]:
    """
    Sandbox executor: validates through MCP and shapes final structural RCA reports.
    """
    new_retry = state.get("retry_counter", 0) + 1
    proposed_patch = state.get("proposed_patch", "# No valid engineering patch produced")

    try:
        sandbox_result = call_mcp_tool(
            "verify_sandbox_patch",
            {
                "command": "python -m py_compile",
                "proposed_patch": proposed_patch,
                "target_file": state.get("target_file", "UNKNOWN"),
            },
        )
    except Exception as e:
        logger.error(f"MCP sandbox verification failed: {e}", exc_info=True)
        sandbox_result = {
            "exit_code": -1,
            "is_fixed": False,
            "output": f"MCP sandbox verification failed: {str(e)}",
        }

    fixed = bool(sandbox_result.get("is_fixed"))
    status_label = "RESOLVED" if fixed else "UNRESOLVED"
    incident_context = state.get("incident_context", {})
    repository_context = state.get("repository_context", {})
    slack_context = state.get("slack_context", {})
    source_modes = state.get("source_modes", {})

    report = f"""# 📝 ROOT CAUSE ANALYSIS (RCA) REPORT
## System Alert Status: {status_label} ({state.get('priority_level', 'UNKNOWN')})
* **Incident Tracking ID:** {state.get('incident_id', 'UNKNOWN')}
* **Alert Trigger Origin:** {state.get('source_system', 'UNKNOWN').upper()}
* **Target Broken Resource:** `{state.get('target_file', 'UNKNOWN')}`
* **Blame Vector (Author):** @{state.get('commit_author', 'UNKNOWN')}
* **Source Modes:** GitHub={source_modes.get('github', 'unknown')}, Datadog={source_modes.get('datadog', 'unknown')}, Slack={source_modes.get('slack', 'unknown')}

### 🔍 Technical Diagnosis
The infrastructure processing framework caught an execution fault trace. Sentinel-Agent routed incident, repository, sandbox, and Slack context through the MCP server before generating this RCA.

MCP Incident Context:
{incident_context}

MCP Repository Context Summary:
- Dependency refs: {repository_context.get('global_dependencies', []) if isinstance(repository_context, dict) else []}
- Timeline entries: {len(repository_context.get('timeline_history', [])) if isinstance(repository_context, dict) else 0}

MCP Slack Context:
{slack_context}

### 🛠️ Mitigation Strategy Applied
Sandbox Verification: exit_code={sandbox_result.get('exit_code')}, is_fixed={fixed}
Output: {sandbox_result.get('output', '(no output)')}

### 👨‍💻 Proposed Patch Changes (Reviewed & Approved)
```python
{proposed_patch}
"""

    try:
        slack_notification_payload = call_mcp_tool(
            "send_slack_rca",
            {
                "incident_id": state.get("incident_id", "UNKNOWN"),
                "rca_report": report,
            },
        )
        slack_notification = slack_notification_payload.get("slack_notification", slack_notification_payload)
        if slack_notification_payload.get("source_modes"):
            source_modes = slack_notification_payload["source_modes"]
    except Exception as e:
        logger.error(f"MCP Slack notification failed: {e}", exc_info=True)
        slack_notification = {"sent": False, "error": str(e)}

    return {
        "retry_counter": new_retry,
        "is_fixed": fixed,
        "final_rca_report": report,
        "sandbox_result": sandbox_result,
        "slack_notification": slack_notification,
        "source_modes": source_modes,
    }
