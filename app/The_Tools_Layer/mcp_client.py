"""
Synchronous wrapper around the local FastMCP stdio server.

LangGraph nodes are synchronous, so this module hides the async MCP client
details and keeps every tool/data lookup behind the MCP protocol boundary.
"""

import asyncio
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict

from fastmcp.client import Client
from fastmcp.client.transports import PythonStdioTransport


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MCP_SERVER_PATH = PROJECT_ROOT / "app" / "The_Tools_Layer" / "devops_mcp_server.py"


def _result_to_data(result: Any) -> Any:
    if getattr(result, "data", None) is not None:
        return result.data
    if getattr(result, "structured_content", None) is not None:
        return result.structured_content

    content = getattr(result, "content", []) or []
    if content:
        text = getattr(content[0], "text", "")
        if text:
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return {"text": text}
    return {}


async def _call_tool_async(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT)
    transport = PythonStdioTransport(
        script_path=MCP_SERVER_PATH,
        env=env,
        cwd=str(PROJECT_ROOT),
        keep_alive=False,
    )
    client = Client(transport)
    async with client:
        result = await client.call_tool(tool_name, arguments)
        data = _result_to_data(result)
        if isinstance(data, dict):
            return data
        return {"result": data}


def call_mcp_tool(tool_name: str, arguments: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    Call a local MCP tool from sync LangGraph node code.
    If invoked under an existing event loop, run the async client in a worker thread.
    """
    payload = arguments or {}
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(_call_tool_async(tool_name, payload))

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(lambda: asyncio.run(_call_tool_async(tool_name, payload)))
        return future.result()

