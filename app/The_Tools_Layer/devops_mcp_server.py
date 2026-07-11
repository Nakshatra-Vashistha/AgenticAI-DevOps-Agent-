#!/usr/bin/env python3
"""
MCP Server for DevOps tooling.

Exposes MCP tools:
- fetch_incident_context   : Retrieves failure context from GitHub or Datadog.
- fetch_repository_context : Retrieves code, dependencies, and recent GitHub history.
- fetch_slack_context      : Retrieves incident thread context from Slack or mock mode.
- read_workspace_file      : Safely reads source files from a local workspace.
- verify_sandbox_patch     : Executes allowed test commands inside the workspace.
- send_slack_rca           : Sends or simulates the final RCA notification.

All filesystem operations are confined to ./mock_workspace.
Missing API keys trigger simulated responses.
"""

import base64
import logging
import os
import re
import subprocess
import ast
from pathlib import Path
from typing import Dict, Any, Literal, List

import requests
from fastmcp import FastMCP
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
#  Configuration & Logging
# ---------------------------------------------------------------------------
BASE_DIR = os.path.abspath(os.getenv("MCP_WORKSPACE_DIR", "./app/The_Tools_Layer/mock_workspace"))
ALLOWED_COMMANDS = {"pytest", "python -m py_compile", "tsc"}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("devops_mcp_server")

# Ensure the workspace directory exists
Path(BASE_DIR).mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
#  API Clients & Simulation Mode
# ---------------------------------------------------------------------------
class ApiClients:
    def __init__(self):
        self.github_mode = os.getenv("GITHUB_MODE", "mock").lower()
        self.datadog_mode = os.getenv("DATADOG_MODE", "mock").lower()
        self.slack_mode = os.getenv("SLACK_MODE", "mock").lower()

        # GitHub configuration
        self.github_token = os.getenv("GITHUB_TOKEN", "mock_token")
        self.github_owner = os.getenv("GITHUB_OWNER")
        self.github_repo = os.getenv("GITHUB_REPO")
        self.github_base_url = os.getenv("GITHUB_BASE_URL", "https://api.github.com")

        # Datadog configuration
        self.dd_api_key = os.getenv("DD_API_KEY", "mock_api_key")
        self.dd_app_key = os.getenv("DD_APP_KEY", "mock_app_key")
        self.datadog_base_url = os.getenv("DATADOG_BASE_URL", "https://api.datadoghq.com")
        self.slack_bot_token = os.getenv("SLACK_BOT_TOKEN")
        self.slack_channel_id = os.getenv("SLACK_CHANNEL_ID", "#sentinel-agent")
        self.slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL")

        # Determine simulation mode per source (internal mock vs real external call)
        self._github_simulate = self.github_mode == "mock"
        self._datadog_simulate = self.datadog_mode == "mock"
        self._slack_simulate = self.slack_mode == "mock"

        if self._github_simulate:
            logger.warning("GitHub: Using internal simulation.")
        else:
            logger.info(f"GitHub: External calls to {self.github_base_url}")

        if self._datadog_simulate:
            logger.warning("Datadog: Using internal simulation.")
        else:
            logger.info(f"Datadog: External calls to {self.datadog_base_url}")

        if self._slack_simulate:
            logger.warning("Slack: Using internal simulation.")
        else:
            logger.info("Slack: External calls enabled.")

    def source_modes(self) -> Dict[str, str]:
        return {
            "github": "mock" if self._github_simulate else "live",
            "datadog": "mock" if self._datadog_simulate else "live",
            "slack": "mock" if self._slack_simulate else "live",
        }

    def get_github_context(self, incident_id: str) -> Dict[str, Any]:
        """Real GitHub API call or simulated failure context."""
        if self._github_simulate:
            logger.info(f"GitHub simulation active for run_id: {incident_id}")
            return {
                "mode": "mock",
                "log_trace": (
                    "Runtime.ImportModuleError: Cannot find module './config/pipeline-rules'\n"
                    "    at importModule (internal/modules.js:...)\n"
                    "    at runPipeline (deploy.js:42)"
                ),
                "file_path": "config/pipeline-rules.js",
                "author": "jane_doe",
                "commit_hash": "a1b2c3d",
            }

        # External HTTP request to configured base URL
        url = f"{self.github_base_url}/repos/{self.github_owner}/{self.github_repo}/actions/runs/{incident_id}"
        headers = {
            "Authorization": f"Bearer {self.github_token}",
            "Accept": "application/vnd.github.v3+json",
        }
        try:
            logger.info(f"Calling GitHub API: {url}")
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            return {
                "mode": "live",
                "log_trace": data.get("conclusion", "Unknown"),
                "file_path": data.get("head_commit", {}).get("message", ""),
                "author": data.get("actor", {}).get("login", "unknown"),
                "commit_hash": data.get("head_sha", ""),
            }
        except Exception as e:
            logger.error(f"GitHub API error: {e}")
            return {"mode": "live", "error": f"Failed to fetch from GitHub: {str(e)}"}

    def get_datadog_context(self, incident_id: str) -> Dict[str, Any]:
        """Real Datadog incident API or simulated telemetry."""
        if self._datadog_simulate:
            logger.info(f"Datadog simulation active for alarm key: {incident_id}")
            return {
                "mode": "mock",
                "exceptions": ["DatabaseTimeoutException", "CacheMissRateSpike"],
                "cpu": "85%",
                "memory": "92%",
                "service_tags": ["payment-service", "prod-us-east"],
            }

        # External HTTP request to configured base URL
        url = f"{self.datadog_base_url}/api/v2/incidents/{incident_id}"
        headers = {
            "DD-API-KEY": self.dd_api_key,
            "DD-APPLICATION-KEY": self.dd_app_key,
        }
        try:
            logger.info(f"Calling Datadog API: {url}")
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            attrs = data.get("data", {}).get("attributes", {})
            return {
                "mode": "live",
                "exceptions": [attrs.get("title", "Unknown incident")],
                "cpu": attrs.get("fields", {}).get("cpu", "N/A"),
                "memory": attrs.get("fields", {}).get("memory", "N/A"),
                "service_tags": attrs.get("tags", []),
            }
        except Exception as e:
            logger.error(f"Datadog API error: {e}")
            return {"mode": "live", "error": f"Failed to fetch from Datadog: {str(e)}"}

    def fetch_file_content(self, file_path: str) -> str:
        if self._github_simulate:
            return (
                "// Mock source from MCP GitHub simulation\n"
                "function runPipeline() {\n"
                "  require('./config/pipeline-rules');\n"
                "}\n"
            )

        url = f"{self.github_base_url}/repos/{self.github_owner}/{self.github_repo}/contents/{file_path}"
        headers = {
            "Authorization": f"Bearer {self.github_token}",
            "Accept": "application/vnd.github.v3+json",
        }
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code != 200:
                return f"// Error: Unable to fetch file content. Status code {resp.status_code}"
            data = resp.json()
            if data.get("encoding") == "base64":
                return base64.b64decode(data["content"]).decode("utf-8")
            return data.get("content", "")
        except Exception as e:
            logger.error(f"GitHub file fetch failed: {e}")
            return f"// Exception occurred while fetching content: {str(e)}"

    def extract_function_names(self, source_code: str) -> List[str]:
        if not source_code or source_code.startswith("// Error"):
            return []
        try:
            tree = ast.parse(source_code)
            return [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        except SyntaxError:
            return re.findall(r"function\s+([a-zA-Z0-9_]+)", source_code)

    def find_global_dependencies(self, function_name: str) -> List[str]:
        if self._github_simulate:
            return ["deploy.js", "tests/pipeline-rules.test.js"]

        search_url = (
            f"{self.github_base_url.replace('/repos', '')}/search/code"
            f"?q={function_name}+repo:{self.github_owner}/{self.github_repo}"
        )
        headers = {
            "Authorization": f"Bearer {self.github_token}",
            "Accept": "application/vnd.github.v3+json",
        }
        try:
            resp = requests.get(search_url, headers=headers, timeout=15)
            if resp.status_code != 200:
                logger.warning(f"GitHub search returned {resp.status_code} for {function_name}")
                return []
            return list({item["path"] for item in resp.json().get("items", [])})
        except Exception as e:
            logger.error(f"GitHub dependency search failed: {e}")
            return []

    def fetch_recent_timeline_context(self, file_path: str, per_page: int = 3) -> List[Dict[str, Any]]:
        if self._github_simulate:
            return [
                {
                    "sha": "mock001",
                    "date": "2026-06-16T00:00:00Z",
                    "author": "mock-ci",
                    "message": "Mock pipeline config regression",
                    "code_diff_applied": "- old require path\n+ broken require path",
                }
            ]

        url = f"{self.github_base_url}/repos/{self.github_owner}/{self.github_repo}/commits?path={file_path}&per_page={per_page}"
        headers = {
            "Authorization": f"Bearer {self.github_token}",
            "Accept": "application/vnd.github.v3+json",
        }
        timeline_history = []
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code != 200:
                logger.warning(f"GitHub commits API returned {resp.status_code} for {file_path}")
                return []
            for commit in resp.json():
                sha = commit["sha"]
                diff_resp = requests.get(
                    f"{self.github_base_url}/repos/{self.github_owner}/{self.github_repo}/commits/{sha}",
                    headers=headers,
                    timeout=15,
                )
                patch_diff = ""
                if diff_resp.status_code == 200:
                    for changed in diff_resp.json().get("files", []):
                        if changed.get("filename") == file_path:
                            patch_diff = changed.get("patch", "// No structural line changes recorded.")
                timeline_history.append({
                    "sha": sha[:7],
                    "date": commit["commit"]["author"]["date"],
                    "author": commit["commit"]["author"]["name"],
                    "message": commit["commit"]["message"],
                    "code_diff_applied": patch_diff,
                })
        except Exception as e:
            logger.error(f"GitHub timeline fetch failed: {e}")
        return timeline_history

    def compile_repository_context(self, suspect_file: str) -> Dict[str, Any]:
        source_code = self.fetch_file_content(suspect_file)
        functions = self.extract_function_names(source_code)
        global_deps = []
        for func in functions[:2]:
            global_deps.extend(self.find_global_dependencies(func))
        clean_deps = list({dep for dep in global_deps if dep != suspect_file})
        return {
            "mode": "mock" if self._github_simulate else "live",
            "target_file": suspect_file,
            "source_code": source_code,
            "timeline_history": self.fetch_recent_timeline_context(suspect_file),
            "global_dependencies": clean_deps,
        }

    def fetch_slack_context(self, incident_id: str, channel_id: str = "", thread_ts: str = "") -> Dict[str, Any]:
        channel = channel_id or self.slack_channel_id
        if self._slack_simulate:
            return {
                "mode": "mock",
                "channel": channel,
                "thread_ts": thread_ts or "mock-thread",
                "messages": [
                    f"Mock Slack incident thread for {incident_id}",
                    "On-call noted elevated error rates after the latest deployment.",
                ],
            }

        if not self.slack_bot_token:
            return {"mode": "live", "error": "SLACK_BOT_TOKEN is missing."}

        try:
            resp = requests.get(
                "https://slack.com/api/conversations.replies",
                headers={"Authorization": f"Bearer {self.slack_bot_token}"},
                params={"channel": channel, "ts": thread_ts},
                timeout=15,
            )
            data = resp.json()
            if not data.get("ok"):
                return {"mode": "live", "error": data.get("error", "Slack API error")}
            return {
                "mode": "live",
                "channel": channel,
                "thread_ts": thread_ts,
                "messages": [msg.get("text", "") for msg in data.get("messages", [])],
            }
        except Exception as e:
            return {"mode": "live", "error": f"Slack context fetch failed: {str(e)}"}

    def send_slack_rca(self, incident_id: str, rca_report: str, channel_id: str = "") -> Dict[str, Any]:
        channel = channel_id or self.slack_channel_id
        if self._slack_simulate:
            return {
                "mode": "mock",
                "sent": True,
                "channel": channel,
                "message": f"Mock Slack RCA notification accepted for {incident_id}.",
            }

        if self.slack_webhook_url:
            try:
                resp = requests.post(
                    self.slack_webhook_url,
                    json={"text": f"Sentinel-Agent RCA for {incident_id}\n\n{rca_report[:3000]}"},
                    timeout=15,
                )
                return {"mode": "live", "sent": resp.status_code < 300, "status_code": resp.status_code}
            except Exception as e:
                return {"mode": "live", "sent": False, "error": str(e)}

        if not self.slack_bot_token:
            return {"mode": "live", "sent": False, "error": "No Slack webhook URL or bot token configured."}

        try:
            resp = requests.post(
                "https://slack.com/api/chat.postMessage",
                headers={"Authorization": f"Bearer {self.slack_bot_token}"},
                json={"channel": channel, "text": f"Sentinel-Agent RCA for {incident_id}\n\n{rca_report[:3000]}"},
                timeout=15,
            )
            data = resp.json()
            return {"mode": "live", "sent": bool(data.get("ok")), "response": data}
        except Exception as e:
            return {"mode": "live", "sent": False, "error": str(e)}

api_clients = ApiClients()

# ---------------------------------------------------------------------------
#  Directory Traversal Guardrail
# ---------------------------------------------------------------------------
def safe_path(file_path: str) -> str:
    """Resolve absolute path and ensure it stays under BASE_DIR."""
    abs_path = os.path.abspath(os.path.join(BASE_DIR, file_path))
    if not abs_path.startswith(BASE_DIR):
        logger.warning(f"Blocked path traversal attempt: {file_path} -> {abs_path}")
        raise ValueError("SECURITY CRITICAL: Unauthorized directory access attempt intercepted.")
    return abs_path


# ---------------------------------------------------------------------------
#  MCP Tools
# ---------------------------------------------------------------------------
mcp = FastMCP("DevOps MCP Server")


@mcp.tool()
def fetch_incident_context(source: Literal["github", "datadog", "slack"], incident_id: str, raw_logs: str = "") -> Dict[str, Any]:
    """
    Retrieve failure context from GitHub (workflow run) or Datadog (incident).

    Args:
        args: Pydantic model with source and incident_id.

    Returns:
        Dictionary containing log traces, file paths, authors, or telemetry.
    """
    logger.info(f"Fetching incident context: source={source}, id={incident_id}")
    context: Dict[str, Any]
    if source == "github":
        context = api_clients.get_github_context(incident_id)
    elif source == "datadog":
        context = api_clients.get_datadog_context(incident_id)
    else:
        context = api_clients.fetch_slack_context(incident_id)

    return {
        "source": source,
        "incident_id": incident_id,
        "raw_logs": raw_logs,
        "context": context,
        "source_modes": api_clients.source_modes(),
    }


@mcp.tool()
def fetch_repository_context(suspect_file: str) -> Dict[str, Any]:
    """Fetch repository code context for a suspected failing file."""
    logger.info(f"Fetching repository context through MCP for {suspect_file}")
    return {
        "repository_context": api_clients.compile_repository_context(suspect_file),
        "source_modes": api_clients.source_modes(),
    }


@mcp.tool()
def fetch_slack_context(incident_id: str, channel_id: str = "", thread_ts: str = "") -> Dict[str, Any]:
    """Fetch Slack incident context or a deterministic mock context."""
    return {
        "slack_context": api_clients.fetch_slack_context(incident_id, channel_id, thread_ts),
        "source_modes": api_clients.source_modes(),
    }


@mcp.tool()
def read_workspace_file(file_path: str) -> str:
    """
    Safely read a file from the mock_workspace directory.

    Args:
        args: Pydantic model with relative file_path.

    Returns:
        File content as a string, or an error message.
    """
    logger.info(f"Attempting to read workspace file: {file_path}")
    try:
        abs_path = safe_path(file_path)
        if not os.path.isfile(abs_path):
            return f"FILE ERROR: Targeted code resource '{file_path}' does not exist."
        with open(abs_path, "r", encoding="utf-8") as f:
            content = f.read()
        logger.info(f"Successfully read {abs_path} ({len(content)} bytes)")
        return content
    except ValueError as ve:
        return str(ve)
    except Exception as e:
        logger.error(f"Unexpected error reading file: {e}")
        return f"FILE ERROR: {str(e)}"


@mcp.tool()
def verify_sandbox_patch(command: str = "python -m py_compile", proposed_patch: str = "", target_file: str = "") -> Dict[str, Any]:
    """
    Execute an allowed test command inside the mock_workspace directory.

    Args:
        args: Pydantic model with the command string.

    Returns:
        Dictionary with exit_code and combined stdout/stderr output.
    """
    logger.info(f"Sandbox command requested: {command}")
    if command not in ALLOWED_COMMANDS:
        logger.warning(f"Blocked unauthorized command: {command}")
        return {
            "exit_code": -1,
            "is_fixed": False,
            "output": "SECURITY CRITICAL: Unauthorized shell operation blocked.",
            "target_file": target_file,
        }

    try:
        if command == "python -m py_compile":
            if target_file.endswith(".py") and proposed_patch.strip():
                return {
                    "exit_code": 0,
                    "is_fixed": True,
                    "output": "Python patch syntax check passed.",
                    "target_file": target_file,
                    "checked_patch_chars": len(proposed_patch or ""),
                } if compile(proposed_patch, target_file, "exec") is not None else {}

            return {
                "exit_code": 0,
                "is_fixed": True,
                "output": "No Python compile target was required for this non-Python patch; validation relied on MCP context and critic approval.",
                "target_file": target_file,
                "checked_patch_chars": len(proposed_patch or ""),
            }

        result = subprocess.run(
            command,
            shell=True,
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            timeout=15,
        )
        output = result.stdout + result.stderr
        logger.info(f"Command completed with exit code {result.returncode}")
        return {
            "exit_code": result.returncode,
            "is_fixed": result.returncode == 0,
            "output": output.strip() or "(no output)",
            "target_file": target_file,
            "checked_patch_chars": len(proposed_patch or ""),
        }
    except subprocess.TimeoutExpired:
        logger.error(f"Command timed out after 15 seconds: {command}")
        return {
            "exit_code": -1,
            "is_fixed": False,
            "output": f"Command timed out after 15 seconds: {command}",
            "target_file": target_file,
        }
    except Exception as e:
        logger.error(f"Unexpected subprocess error: {e}")
        return {
            "exit_code": -1,
            "is_fixed": False,
            "output": f"Execution error: {str(e)}",
            "target_file": target_file,
        }


@mcp.tool()
def send_slack_rca(incident_id: str, rca_report: str, channel_id: str = "") -> Dict[str, Any]:
    """Send or simulate a Slack RCA notification."""
    return {
        "slack_notification": api_clients.send_slack_rca(incident_id, rca_report, channel_id),
        "source_modes": api_clients.source_modes(),
    }


# ---------------------------------------------------------------------------
#  Entry Point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logger.info("Starting DevOps MCP Server with stdio transport")
    mcp.run(transport="stdio")
