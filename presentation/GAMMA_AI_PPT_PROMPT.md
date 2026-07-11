# Gamma AI Presentation Prompt — Sentinel-Agent

Copy everything below into Gamma AI.

---

Create a polished, technically credible 15-slide presentation for the software project described below.

## Presentation objective

Present **Sentinel-Agent**, an AI-powered autonomous DevOps incident-response and self-healing orchestration system. The audience is a technical evaluation panel, professors, hackathon judges, engineering leaders, or potential adopters. The presentation should explain the problem, show the real implemented architecture, demonstrate the workflow, highlight safety controls, and close with current status and future scope.

The presentation should feel like a serious engineering product pitch—not a generic AI slideshow.

## Non-negotiable accuracy rules

- Use only the project facts supplied in this prompt.
- Do not invent customers, users, revenue, benchmarks, accuracy rates, MTTR reductions, test coverage, production scale, or performance percentages.
- Do not claim that Sentinel-Agent directly commits, merges, or deploys generated code. The current implementation generates a proposed patch, reviews it, validates it, produces an RCA, and sends or simulates a Slack notification.
- Do not call the system fully production-ready. Describe it as a working prototype with live-integration support and deterministic mock modes.
- Pinecone episodic memory is implemented as a standalone module but is not currently connected to the active LangGraph workflow. Present it under “Extensibility / Next Steps,” not as an active step on every incident.
- A separate GitHub deep-context orchestrator exists, while the active graph obtains equivalent repository context through the MCP server. Make this distinction only if needed.
- The FastAPI webhook currently invokes the workflow synchronously before returning its result. Do not describe it as a deployed message-queue or background-worker architecture.
- The sandbox performs a real Python syntax compilation check for Python patches. For non-Python patches, the current fallback records successful validation based on MCP context and critic approval; do not imply that JavaScript or TypeScript patches are fully compiled in the current default path.
- The project supports Gemini or Grok through an LLM factory. The default provider is Gemini, with the model selected through environment configuration.

## Project identity

**Name:** Sentinel-Agent  
**Category:** Agentic AI, DevOps Automation, Site Reliability Engineering, Incident Response  
**One-line description:** An autonomous multi-agent DevOps pipeline that transforms an incident alert into contextual diagnosis, a reviewed repair proposal, sandbox validation, and a structured root-cause analysis report.  
**Tagline:** “From production alert to reviewed repair and RCA—through one controlled agent workflow.”

## The problem

Modern incident response is fragmented and slow:

- Alerts arrive from monitoring systems, CI/CD pipelines, or collaboration channels.
- Engineers manually correlate logs, source files, dependencies, commit history, and team discussions.
- A rushed fix can introduce regressions.
- Generic LLMs may lack repository context, repeat rejected ideas, or execute unsafe operations.
- Root-cause reports and stakeholder updates are often written manually after the incident.

The engineering challenge is not simply generating code. It is coordinating diagnosis, context retrieval, repair, review, validation, and communication safely.

## The solution

Sentinel-Agent creates a controlled incident-response pipeline:

1. Accept an incident through a FastAPI webhook or interactive terminal runner.
2. Pass a strict shared state through a LangGraph workflow.
3. Retrieve GitHub, Datadog, repository, and Slack context through a local FastMCP tool server.
4. Use an SRE Analyst agent to identify the likely failing file and priority.
5. Use a Repair Engineer agent to generate a proposed code patch with source, dependency, commit-history, and past-critique context.
6. Use a Code Critic agent to approve or reject the patch.
7. Loop rejected patches back to the Repair Engineer, with a maximum of three critic rejections.
8. Use a Sandbox Coordinator to validate the patch through an allow-listed tool.
9. Generate a Markdown root-cause analysis report.
10. Send or simulate the RCA notification through Slack.

## Implemented entry points

### FastAPI gateway

- `GET /health`
- `POST /webhook/incident`
- Webhook input schema:
  - `incident_id`
  - `source_system`
  - `raw_logs`
- The response includes:
  - target file
  - priority
  - fix status
  - source modes
  - incident context
  - sandbox result
  - Slack notification result
  - proposed patch
  - final RCA report

### Terminal runner

The `run_pipeline.py` script accepts:

- incident tracking ID
- source system: GitHub, Datadog, or Slack
- multiline crash logs or stack traces

It invokes the same LangGraph engine and prints the final RCA.

## Active LangGraph architecture

Use a prominent workflow diagram:

**Incident Input → SRE Analyst → Repair Engineer → Code Critic**

From Code Critic:

- **Approved → Sandbox Coordinator → RCA + Slack → End**
- **Rejected → Repair Engineer**, carrying accumulated feedback
- After three critic rejections, force routing to the sandbox to protect API/token limits

The graph has four active nodes:

1. **SRE Analyst**
   - Calls MCP for incident context.
   - Calls MCP for Slack context.
   - Detects Python, JavaScript, or TypeScript filenames in logs using regex.
   - Uses incident context or known import-error rules as fallback.
   - Uses the LLM when deterministic methods cannot identify the target.
   - Produces target file, priority, and author/blame metadata.

2. **Repair Engineer**
   - Retrieves current source code through MCP.
   - Retrieves global dependency references.
   - Retrieves recent file commit history and code diffs.
   - Includes all prior critic feedback so rejected approaches are not repeated.
   - Generates only the proposed executable code, with markdown fences removed.

3. **Code Critic**
   - Compares the proposed patch with the original incident logs.
   - Returns APPROVED or REJECTED with feedback.
   - Stores rejection feedback in the shared state.
   - Supports a bounded repair-review loop.

4. **Sandbox Coordinator**
   - Calls the MCP sandbox verification tool.
   - Records exit code, output, target file, and fix status.
   - Generates the final Markdown RCA.
   - Calls the MCP Slack notification tool.

## Shared state contract

LangGraph passes a typed `DevOpsAgentState` containing:

- incident ID, source system, and raw logs
- incident context
- repository context
- Slack context
- source modes
- target file
- commit author
- priority level
- proposed patch
- critic feedback history
- critic approval flag
- retry counter
- sandbox result
- fix status
- Slack notification result
- final RCA report

The project uses explicit overwrite reducers so node updates have predictable state semantics during loop-back transitions.

## MCP tool layer

The active tool layer is a local **FastMCP server using stdio transport**. A synchronous wrapper lets the synchronous LangGraph nodes call asynchronous MCP tools. If an event loop already exists, the wrapper runs the MCP call in a worker thread.

The MCP server exposes six tools:

1. `fetch_incident_context`
   - Retrieves GitHub workflow-run context, Datadog incident telemetry, or Slack context.

2. `fetch_repository_context`
   - Retrieves target source code.
   - Extracts function names using Python AST, with regex fallback for JavaScript.
   - Searches for dependent files.
   - retrieves recent commits and diffs for the target file.

3. `fetch_slack_context`
   - Retrieves incident-thread context or returns deterministic mock messages.

4. `read_workspace_file`
   - Reads only from the configured mock workspace.

5. `verify_sandbox_patch`
   - Allows only `pytest`, `python -m py_compile`, or `tsc`.
   - The active graph currently requests `python -m py_compile`.
   - Python patch text is compiled in memory for syntax validation.

6. `send_slack_rca`
   - Sends the RCA through a webhook or Slack API, or simulates the delivery in mock mode.

Explain why MCP matters: it separates model reasoning from external tools and credentials, gives tools a consistent protocol boundary, and makes live integrations replaceable with safe mocks.

## External integrations and modes

Sentinel-Agent is designed for:

- **GitHub**
  - workflow-run incident context
  - file content retrieval
  - global code search for dependencies
  - file-specific commit history
  - commit diff retrieval

- **Datadog**
  - incident metadata
  - exceptions
  - CPU and memory telemetry
  - service tags

- **Slack**
  - incident-thread context
  - final RCA delivery

Each source has an independent `mock` or `live` mode configured through environment variables. Mock mode returns deterministic data, making demos and local development possible without exposing real credentials or depending on external service availability.

## Security and reliability controls

Create one slide focused on concrete guardrails:

- **Directory confinement:** filesystem access is restricted to a configured workspace directory.
- **Path traversal protection:** requested paths are converted to absolute paths and checked against the workspace boundary.
- **Command allow-list:** only `pytest`, `python -m py_compile`, and `tsc` are accepted by the MCP sandbox tool.
- **Execution timeout:** subprocess commands have a 15-second timeout.
- **Bounded review loop:** a maximum of three critic rejections prevents uncontrolled token/API consumption.
- **Low-temperature LLM configuration:** Gemini uses temperature 0.2 for more deterministic engineering output.
- **Credential isolation:** API keys are loaded from environment variables and tool access is kept behind the MCP layer.
- **Mock/live isolation:** demos can run without hitting production services.
- **Strict patch-output prompts:** the Repair Engineer is instructed to return code only.

Use measured language: these controls reduce risk; they do not make arbitrary AI-generated changes automatically safe.

## Context engineering advantage

Emphasize that Sentinel-Agent does not indiscriminately load an entire codebase into the model. It retrieves targeted context:

- suspected failing file
- current source code
- functions defined in that file
- repository files that reference those functions
- recent commits touching that file
- exact patch diffs from those commits
- original crash logs
- prior critic rejections
- related Slack discussion

This creates a compact, incident-specific context package and helps detect recent regressions while limiting irrelevant context and token usage.

## LLM provider architecture

The `LLMBrainFactory` supports:

- Google Gemini through `ChatGoogleGenerativeAI`
- Grok through an OpenAI-compatible `ChatOpenAI` client pointed at the xAI API

Provider and model selection are controlled by environment variables. The active default is Gemini. This keeps the agent orchestration independent from one model vendor.

## Final RCA output

The generated Markdown RCA includes:

- resolved or unresolved status
- priority
- incident tracking ID
- trigger source
- target resource
- identified author/blame vector
- GitHub, Datadog, and Slack source modes
- incident context
- repository dependency summary
- number of timeline entries
- Slack context
- sandbox exit code and output
- proposed reviewed patch

The same structured result is also exposed in the FastAPI JSON response.

## Technology stack

Show a clean layered stack:

- **Language:** Python
- **API gateway:** FastAPI, Pydantic, Uvicorn
- **Agent orchestration:** LangGraph, LangChain Core
- **LLMs:** Google Gemini or Grok
- **Tool protocol:** FastMCP / Model Context Protocol
- **HTTP integrations:** Requests and HTTPX
- **Memory extension:** Pinecone and Google embeddings
- **Configuration:** python-dotenv and environment variables
- **External systems:** GitHub, Datadog, Slack

## Current implementation status

Implemented:

- FastAPI health and incident webhook endpoints
- terminal-based pipeline runner
- typed LangGraph state
- four-agent/node workflow
- bounded critic-repair loop
- local stdio MCP server and client wrapper
- six MCP tools
- GitHub, Datadog, and Slack live/mock adapters
- targeted repository context retrieval
- sandbox command restrictions
- RCA generation
- Slack delivery or simulation
- model-provider factory
- standalone Pinecone episodic-memory module

Current limitations:

- generated patches are not automatically written to the real repository
- no automatic commit, pull request, merge, rollback, or deployment
- Pinecone memory is not connected to the active graph
- the webhook execution is synchronous
- the default active sandbox request is strongest for Python syntax validation
- no production benchmark or quantified MTTR result has been established
- human approval and stronger isolated execution would be required before production remediation

## Roadmap

Present a realistic roadmap:

1. Connect Pinecone memory to retrieve similar past incidents before patch generation and store successful resolutions afterward.
2. Replace synchronous webhook processing with a durable queue and background workers.
3. Add containerized or ephemeral sandbox execution with language-specific test suites.
4. Add a human approval gate before repository mutation.
5. Generate a pull request instead of only returning a patch.
6. Add observability for agent traces, tool latency, token cost, and outcomes.
7. Add authentication, authorization, secret management, audit logs, and tenant isolation.
8. Expand integrations to Kubernetes, cloud platforms, PagerDuty, and additional CI systems.
9. Evaluate against a repeatable incident benchmark and measure diagnosis quality, patch validity, and time-to-RCA.

## Slide structure

Build exactly these slides:

### Slide 1 — Title

Title: **Sentinel-Agent**  
Subtitle: **Autonomous, Context-Aware DevOps Incident Response**  
Tagline: **From production alert to reviewed repair and RCA—through one controlled agent workflow.**

Visual: dark operations-command-center aesthetic with an alert flowing through AI agents toward a verified report.

### Slide 2 — The Incident Response Gap

Show the fragmented manual process: Alert → logs → repository → commit history → team chat → patch → tests → RCA.  
Message: the bottleneck is coordination across systems, not merely code generation.

### Slide 3 — The Sentinel-Agent Solution

Show the complete value proposition in one visual:
**Ingest → Contextualize → Diagnose → Repair → Critique → Validate → Report**

Include three core benefits without fake metrics:

- incident-specific context
- controlled multi-agent reasoning
- protocol-isolated tools and safety guardrails

### Slide 4 — End-to-End Incident Journey

Use a numbered flow from incoming webhook/terminal input to JSON response and Slack RCA. Include GitHub, Datadog, and Slack as data sources.

### Slide 5 — System Architecture

Use a layered architecture diagram:

1. Ingestion Layer — FastAPI and terminal runner
2. State and Orchestration Layer — LangGraph
3. Reasoning Layer — SRE Analyst, Repair Engineer, Code Critic, Sandbox Coordinator
4. Tool Layer — FastMCP server
5. External Systems — GitHub, Datadog, Slack, local sandbox
6. Future Memory Layer — Pinecone, clearly labeled “implemented module; graph integration pending”

### Slide 6 — Multi-Agent Workflow

Feature the four LangGraph nodes and conditional critic loop. Clearly show the three-rejection ceiling.

### Slide 7 — What Each Agent Does

Use four concise cards:

- SRE Analyst
- Repair Engineer
- Code Critic
- Sandbox Coordinator

Give inputs, responsibility, and output for each.

### Slide 8 — MCP: The Controlled Tool Boundary

Explain the local stdio MCP server and six tools. Use a hub-and-spoke visual from the LangGraph client to GitHub, Datadog, Slack, repository context, sandbox, and workspace.

### Slide 9 — Context Engineering for Better Repairs

Show a “context packet” containing logs, target source, dependencies, recent commits/diffs, Slack discussion, and critic feedback. Explain AST extraction and JavaScript regex fallback.

### Slide 10 — Safety by Design

Show the concrete guardrails: workspace confinement, path checks, allow-listed commands, timeout, bounded loop, mock/live separation, environment-based credentials, and no automatic repository mutation.

### Slide 11 — API and Integration Surface

Show:

- `GET /health`
- `POST /webhook/incident`
- terminal runner
- GitHub live/mock
- Datadog live/mock
- Slack live/mock

Include a compact example webhook payload:

```json
{
  "incident_id": "INC-9921",
  "source_system": "github",
  "raw_logs": "Runtime.ImportModuleError: Cannot find module..."
}
```

### Slide 12 — Output: A Structured RCA

Mock up a professional RCA page with status, incident ID, source, target file, context summary, sandbox evidence, proposed patch, and Slack delivery status. State that the API also returns these fields as JSON.

### Slide 13 — Technology Stack and Project Structure

Show the stack and a simplified repository tree:

```text
app/
├── main.py
├── config.py
├── Langgraph_agent_Orchestrator/
│   ├── agents/
│   ├── graph/
│   └── memory/
└── The_Tools_Layer/
    ├── devops_mcp_server.py
    ├── mcp_client.py
    └── github_context_tool.py
```

### Slide 14 — Current Status, Limitations, and Roadmap

Use three columns:

- Working today
- Honest limitations
- Next engineering milestones

Make Pinecone integration, durable workers, container sandboxing, human approval, PR creation, observability, and benchmarking visible.

### Slide 15 — Closing Vision

Headline: **“Incident response should be an orchestrated engineering workflow—not a race across browser tabs.”**

Closing message: Sentinel-Agent demonstrates how specialized agents, targeted repository context, MCP-isolated tools, bounded review loops, and verifiable outputs can form the foundation of safer AI-assisted operations.

End with: **Thank You — Questions?**

## Design direction

- Format: 16:9 widescreen
- Style: modern dark technical theme; premium, minimal, and high contrast
- Color palette:
  - background: near-black/navy
  - primary accent: electric cyan
  - secondary accent: violet
  - success: green
  - warning/incident: coral or amber
- Typography: clean sans-serif such as Inter, Manrope, or IBM Plex Sans
- Use diagrams, data-flow arrows, architecture blocks, code snippets, and UI-style cards.
- Keep each slide visually focused with one dominant idea.
- Avoid long paragraphs. Convert supplied detail into concise visual content.
- Avoid generic humanoid robots, glowing brains, or sci-fi faces.
- Prefer infrastructure imagery: servers, logs, graphs, APIs, repositories, terminal windows, alert badges, and workflow nodes.
- Use consistent icons for FastAPI, LangGraph, MCP, GitHub, Datadog, Slack, Gemini/Grok, and Pinecone.
- Add small footer text: **Sentinel-Agent | Agentic DevOps Incident Response**
- Put technical caveats in small but readable callout boxes where relevant.

## Available project visuals

If the user uploads project screenshots to Gamma, use them selectively:

- `research/Screenshot 2026-05-27 125229.png` — MCP client/server/data-source concept
- `research/Screenshot 2026-05-27 124354.png` — generalized MCP topology
- `research/Screenshot 2026-05-27 114143.png` — security controls reference
- `research/Screenshot 2026-06-03 101415.png` — MCP definition reference
- `research/Screenshot 2026-06-03 123650.png` — webhook reference

Redraw architecture graphics in a consistent visual system instead of inserting low-resolution screenshots as full slides. Use screenshots as small evidence/reference panels only.

## Final quality check

Before generating the deck, verify that:

- all 15 slides are present
- the critic loop and three-rejection ceiling are shown
- all six MCP tools are represented
- mock and live modes are explained
- security controls are concrete
- no unsupported metric is present
- no automatic deployment claim is present
- Pinecone is labeled as pending active-workflow integration
- the current sandbox limitation is accurately described
- the conclusion clearly communicates both innovation and engineering responsibility

