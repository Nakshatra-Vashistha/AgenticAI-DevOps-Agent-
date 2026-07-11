# Sentinel-Agent

Autonomous, Context-Aware DevOps Incident-Response System

https://img.shields.io/badge/python-3.10+-blue.svg

https://img.shields.io/badge/FastAPI-0.115.6-green.svg

https://img.shields.io/badge/LangGraph-0.2.0-orange.svg

https://img.shields.io/badge/License-MIT-yellow.svg


# 📋 Overview

Sentinel-Agent transforms chaotic incident response into a structured, multi-agent pipeline. When production breaks, engineers spend precious time context-switching across tools—logs, repositories, Slack threads, monitoring dashboards. Sentinel-Agent orchestrates this entire lifecycle, from production alert to reviewed repair proposal and root-cause analysis.

The system ingests incidents via webhook or terminal, gathers targeted context through an MCP tool server, routes the incident through four specialized LangGraph agents, and produces a structured RCA with Slack delivery—all in under 11 minutes at a natural speaking pace.

***


# 🎯 The Incident Response Gap

Today, incident response is fragmented across multiple tools:



![Architecture](research/deepseek_mermaid_20260711_bc595f.png)





Every handoff costs time and loses context. Under pressure, teams fix visible symptoms without understanding dependencies or recent changes that caused regressions.

The real problem is not code generation—it's safe coordination across the complete incident lifecycle.

💡 The Sentinel-Agent Solution
Sentinel-Agent turns fragmentation into a structured pipeline built on three core principles:

Principle	Implementation
Targeted Context	Provide incident-specific context instead of dumping entire repositories into prompts
Specialized Agents	Divide responsibility across focused agents rather than asking one model to do everything
Controlled Tool Boundary	Keep external tools and dangerous operations behind a managed MCP interface
End-to-End Incident Journey










🏗️ System Architecture



















Layer Details
Layer	Components	Responsibility
Ingestion	FastAPI, Terminal Runner	Accept incidents via webhook or CLI
Orchestration	LangGraph, Pydantic State	Manage workflow and typed incident state
Reasoning	4 Specialized Agents	Diagnose, repair, critique, validate
Tool	FastMCP Server	Controlled bridge to external services
Memory	Pinecone (Standalone)	Episodic memory for similar incidents (planned integration)
🤖 Multi-Agent Workflow
The Four Agents
Agent	Responsibility	Inputs	Outputs
SRE Analyst	Diagnose incident, identify target file	Logs, source, dependencies	Diagnosis, priority, target file
Repair Engineer	Generate patch proposal	Logs, source, dependencies, diffs, feedback	Patch code
Code Critic	Review proposed patch	Original failure, patch	APPROVED/REJECTED + reason
Sandbox Coordinator	Validate patch, generate RCA	Approved patch	Validation results, RCA
The Critique-Repair Loop







The loop is bounded: After 3 rejections, the router stops the loop and proceeds to terminal validation to protect API limits and prevent uncontrolled agent cycles.

🛠️ MCP: The Controlled Tool Boundary
Model Context Protocol (MCP) provides a consistent, explicit tool boundary between reasoning agents and external services.

Exposed Tools
Tool	Purpose	Mock Mode
incident_context	Retrieve Datadog telemetry	✅
repository_context	Fetch code, dependencies, functions	✅
slack_context	Gather discussion context	✅
workspace_read	Safe file system access	✅
sandbox_verify	Validate patches in restricted environment	✅
slack_deliver	Send final RCA notification	✅
Why MCP Matters:

Models request capabilities through explicit tools

No direct access to credentials, files, or OS

Each integration switches independently between mock and live mode

🧠 Context Engineering
Sentinel-Agent uses targeted context rather than blindly loading entire codebases:









Context Retrieval Process
Identify suspected file from incident

Retrieve current source code and extract function names

Python: AST parser

JavaScript: Regex fallback

Search for repository files referencing those functions

Collect recent commits and exact diffs for the target file

Combine with crash logs, Slack discussion, and previous review feedback

Produce compact, incident-specific context packet

🔒 Safety by Design
Control	Implementation
Filesystem Access	Confined to configured workspace; path traversal blocked
Sandbox Commands	Only pytest, Python compile, TypeScript compile allowed
Execution Timeout	15-second subprocess limit
Critic Loop	Maximum 3 iterations
Credentials	Environment variables only
Mock Mode	Every external source supports deterministic mocks
Repository Mutation	No silent writes, commits, or deployments—only proposal + evidence
⚠️ Important: While these controls reduce risk, production remediation requires stronger isolation, authorization, auditability, and a human approval gate.

📡 API and Integration Surface
Endpoints
http
GET  /health
POST /incident
Input Schema
json
{
  "incident_id": "INC-12345",
  "source": "github|datadog|slack",
  "logs": "Raw incident logs",
  "priority": "P0|P1|P2|P3",
  "context": {
    "repository": "org/repo",
    "service": "service-name",
    "tags": ["production", "api"]
  }
}
Output: Structured RCA
The final product is a Markdown RCA containing:

Incident status, priority, tracking ID

Trigger source, target resource, identified author

Source modes (mock vs. live)

Incident context, repository dependency summary

Slack context, sandbox evidence

Proposed patch

For automated consumers, the FastAPI response also exposes JSON:

json
{
  "status": "completed",
  "patch": "diff --git a/file.py b/file.py...",
  "sandbox_result": "passed",
  "notification_result": "delivered",
  "rca": "# Root Cause Analysis..."
}
🚀 Getting Started
Prerequisites
Python 3.10+

uv (recommended)

API keys for your chosen LLM provider (Gemini or Grok)

Installation
bash
# Clone the repository
git clone https://github.com/yourusername/sentinel-agent.git
cd sentinel-agent

# Install dependencies with uv
uv sync

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys and configuration
Configuration
bash
# Required environment variables
export LLM_PROVIDER="gemini"  # or "grok"
export GEMINI_API_KEY="your-key"
export MCP_SERVER_MODE="mock"  # or "live"
export WORKSPACE_ROOT="/path/to/workspace"

# Optional integrations
export GITHUB_TOKEN="your-token"
export DATADOG_API_KEY="your-key"
export SLACK_WEBHOOK_URL="your-webhook"
export PINECONE_API_KEY="your-key"
Running the Server
bash
# Start the FastAPI server
uv run uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

# Or use the terminal runner for demo
uv run python src/cli.py --incident examples/incident.json
Quick Test
bash
# Send a test incident via curl
curl -X POST http://localhost:8000/incident \
  -H "Content-Type: application/json" \
  -d '{
    "incident_id": "TEST-001",
    "source": "github",
    "logs": "Error: ImportError: No module named 'requests' in api/service.py",
    "priority": "P1"
  }'
📁 Project Structure
text
sentinel-agent/
├── src/
│   ├── agents/              # LangGraph node implementations
│   │   ├── sre_analyst.py
│   │   ├── repair_engineer.py
│   │   ├── code_critic.py
│   │   └── sandbox_coordinator.py
│   ├── graph/               # LangGraph state and workflow
│   │   ├── state.py
│   │   └── workflow.py
│   ├── mcp/                 # FastMCP server and client
│   │   ├── server.py
│   │   ├── client.py
│   │   └── tools/
│   │       ├── github.py
│   │       ├── datadog.py
│   │       ├── slack.py
│   │       └── sandbox.py
│   ├── models/              # LLM provider factory
│   │   ├── provider.py
│   │   └── gemini.py
│   ├── memory/              # Pinecone episodic memory
│   │   └── episodic.py
│   └── main.py              # FastAPI entry point
├── examples/                # Sample incidents
├── tests/                   # Unit and integration tests
├── prompts/                 # Agent prompt templates
├── .env.example
├── pyproject.toml
├── uv.lock
└── README.md
🧪 Technology Stack
Component	Technology
Language	Python 3.10+
Web Framework	FastAPI + Pydantic
Workflow	LangGraph + LangChain
LLM Providers	Gemini, Grok (extensible)
Tool Protocol	FastMCP
HTTP Client	Requests + HTTPX
Configuration	Pydantic Settings + python-dotenv
Monitoring	OpenTelemetry (planned)
Memory	Pinecone (standalone)
🗺️ Roadmap
✅ Current Status (v0.1)
FastAPI webhook + terminal entry points

Four-node LangGraph workflow

Critique-repair loop with bounded iterations

Six MCP tools with mock/live modes

Targeted GitHub context (source, dependencies, diffs)

Sandbox validation (Python compile, pytest)

RCA generation + Slack delivery

Multi-provider model selection

🚧 In Progress
Connect Pinecone episodic memory to active graph

Asynchronous workers (Celery/Redis)

Ephemeral container sandboxes (Docker)

Human approval gate

Pull request generation

🔮 Future Milestones
Improved observability + audit logs

Production-grade isolation (namespace, RBAC)

Repeatable incident benchmark suite

Multi-language deep validation

Web UI for incident visualization

⚠️ Current Limitations
Limitation	Impact	Mitigation
No repository mutation	Cannot create PRs automatically	Manual review required
Synchronous webhook	Long-running requests	Switch to async workers
Pinecone not integrated	No similarity retrieval	Standalone module available
Limited sandbox validation	Non-Python validation is lighter	Add container execution
Default workspace path	Root for all operations	Configure per deployment
🔬 Example RCA Output
markdown
# Root Cause Analysis: INC-12345

## Incident Overview
- **ID**: INC-12345
- **Priority**: P1
- **Status**: Resolved
- **Target**: api/service.py
- **Author**: @developer

## Diagnosis
The SRE Analyst identified an `ImportError` in `api/service.py` caused by a missing `requests` module. This was introduced in commit `abc1234` where the module was removed during a refactor.

## Proposed Patch
```diff
- # Missing import
+ import requests
Sandbox Validation
Python compile: ✅ Passed

pytest: ✅ All tests passed (12/12)

Dependencies
Updated requirements.txt to include requests==2.31.0

No breaking changes detected

Recommendation
Apply patch to resolve import error and restore service functionality.

text

---

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup

```bash
# Install development dependencies
uv sync --dev

# Run tests
uv run pytest

# Format code
uv run black src/ tests/
uv run ruff check src/ tests/

# Run type checking
uv run mypy src/
📄 License
MIT License - see LICENSE for details.

🙏 Acknowledgments
Built with LangGraph and FastMCP

Inspired by the need for safer, more structured AI-assisted operations

📞 Contact
Issues: GitHub Issues

Discussions: GitHub Discussions

Built with ❤️ by the Sentinel-Agent Team
