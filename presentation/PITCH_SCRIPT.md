# Sentinel-Agent Pitch Script

This script follows the 15-slide Gamma deck. At a natural speaking pace, it runs approximately 9–11 minutes.

## Slide 1 — Sentinel-Agent

“Good morning everyone.

This is Sentinel-Agent: an autonomous, context-aware DevOps incident-response system.

When production breaks, the difficult part is rarely just writing one line of code. An engineer has to understand the alert, inspect logs, locate the failing component, study the repository, check recent commits, discuss the incident, propose a fix, review it, validate it, and document the root cause.

Sentinel-Agent brings those activities into one controlled agent workflow—from production alert to a reviewed repair proposal and root-cause analysis.”

## Slide 2 — The Incident Response Gap

“Today, incident response is fragmented across several tools.

An alert may begin in GitHub Actions or Datadog. The engineer then moves to the repository, searches through code, checks commit history, reads a Slack thread, creates a patch, runs tests, and finally writes an RCA.

Every handoff costs time and loses context. Under pressure, teams may fix the visible symptom without understanding dependencies or the recent change that caused the regression.

So the real problem is not simply code generation. It is safe coordination across the complete incident lifecycle.”

## Slide 3 — The Sentinel-Agent Solution

“Sentinel-Agent turns this fragmented process into a structured pipeline.

It ingests an incident, gathers targeted context, diagnoses the likely cause, produces a repair proposal, sends that proposal through an independent critic, validates it through a restricted sandbox, and generates a structured RCA.

The system is built around three ideas.

First, give the model incident-specific context instead of dumping an entire repository into a prompt.

Second, divide responsibility across specialized agents instead of asking one model to do everything.

Third, keep external tools and dangerous operations behind a controlled MCP boundary.”

## Slide 4 — End-to-End Incident Journey

“An incident can enter Sentinel-Agent in two ways: through a FastAPI webhook or through an interactive terminal runner.

The input contains an incident ID, a source such as GitHub, Datadog, or Slack, and the raw logs.

The workflow then retrieves operational and repository context, identifies the target file, generates and reviews a patch, performs sandbox validation, builds an RCA, and sends or simulates a Slack notification.

For API users, the final response also returns the target file, priority, source modes, patch, sandbox result, notification result, and RCA as structured JSON.”

## Slide 5 — System Architecture

“The architecture is organized into clear layers.

At the top is the ingestion layer: FastAPI for webhook traffic and a terminal runner for local demonstrations.

Next is LangGraph, which acts as the state and orchestration layer. It passes one typed incident state through every stage.

The reasoning layer contains four specialized nodes: SRE Analyst, Repair Engineer, Code Critic, and Sandbox Coordinator.

Below them is the FastMCP tool server. It is the controlled bridge to GitHub, Datadog, Slack, repository context, and sandbox execution.

The project also includes a Pinecone episodic-memory module. That module can store and retrieve similar resolved incidents, but its connection to the active graph is a planned next step rather than a current runtime claim.”

## Slide 6 — Multi-Agent Workflow

“The workflow begins with the SRE Analyst and then moves to the Repair Engineer and Code Critic.

The important part is the conditional loop.

If the critic approves the patch, it moves to the Sandbox Coordinator.

If the critic rejects it, the reason is stored in the shared state and sent back to the Repair Engineer. The next repair attempt receives all earlier feedback, so it can avoid repeating the same mistake.

This loop is deliberately bounded. After three rejections, the router stops the loop and proceeds to terminal validation. That protects API limits and prevents uncontrolled agent cycles.”

## Slide 7 — What Each Agent Does

“Each node has one defined responsibility.

The SRE Analyst combines deterministic detection with model reasoning. It checks logs for Python, JavaScript, or TypeScript files, uses MCP incident context, applies known import-error fallbacks, and calls the LLM only when those methods are insufficient.

The Repair Engineer receives the logs, current source, dependencies, recent commit diffs, and previous critic feedback. It returns code only.

The Code Critic compares that patch against the original failure and returns either APPROVED or REJECTED with a reason.

Finally, the Sandbox Coordinator requests validation, records the result, generates the RCA, and sends the notification.”

## Slide 8 — MCP: The Controlled Tool Boundary

“A major part of the project is the MCP tool layer.

The active implementation runs a local FastMCP server over standard input and output. The LangGraph nodes use an MCP client wrapper, so the reasoning code does not directly handle every external integration.

The server exposes six tools: incident context, repository context, Slack context, safe workspace reading, sandbox verification, and Slack RCA delivery.

This boundary matters because models should request capabilities through explicit tools. They should not receive unrestricted access to credentials, files, or the operating system.

It also allows each external source to switch independently between deterministic mock mode and live API mode.”

## Slide 9 — Context Engineering for Better Repairs

“Sentinel-Agent uses targeted context rather than blindly loading a large codebase.

For the suspected file, it retrieves the current source code and extracts function names. Python uses the AST parser, while JavaScript has a regular-expression fallback.

It can then search for repository files that reference those functions and retrieve recent commits and exact diffs for the target file.

That information is combined with the crash logs, Slack discussion, and previous review feedback.

The result is a compact context packet focused on the incident. This helps the Repair Engineer reason about dependencies and recent regressions without spending context on unrelated files.”

## Slide 10 — Safety by Design

“Because this system handles code and execution, its restrictions are as important as its intelligence.

Filesystem access is confined to a configured workspace, and paths are checked to block traversal outside it.

The sandbox accepts only three command forms: pytest, Python compile, and TypeScript compile. Subprocesses have a 15-second timeout.

The critic loop is capped, API credentials come from environment variables, and every external source can operate in mock mode.

Most importantly, the current prototype does not silently write, commit, merge, or deploy a generated patch. It proposes and evaluates a repair, then returns evidence for review.

These controls reduce risk, although production remediation would still require stronger isolation, authorization, auditability, and a human approval gate.”

## Slide 11 — API and Integration Surface

“The integration surface is intentionally simple.

There is a health endpoint and one incident webhook endpoint. A caller sends an incident ID, source system, and raw logs.

The same engine can also be run from the terminal, which is useful for demonstrations and local testing.

GitHub provides workflow and repository context. Datadog provides incident telemetry such as exceptions, resource usage, and service tags. Slack provides discussion context and receives the final RCA.

Each integration reports whether it ran in mock or live mode, and that information is included in the final state and report.”

## Slide 12 — Output: A Structured RCA

“The final product of the workflow is not only a patch.

Sentinel-Agent creates a Markdown RCA containing the incident status, priority, tracking ID, trigger source, target resource, identified author, source modes, incident context, repository dependency summary, Slack context, sandbox evidence, and the proposed patch.

For automated consumers, the FastAPI response exposes these results as JSON as well.

This makes the output useful both to engineers reading a report and to other systems that may archive, display, or route the incident result.”

## Slide 13 — Technology Stack and Project Structure

“The prototype is implemented in Python.

FastAPI and Pydantic provide the ingestion gateway and input validation. LangGraph manages the stateful workflow, and LangChain adapters connect to Gemini or Grok through a provider factory.

FastMCP provides the tool protocol. Requests and HTTPX handle external APIs. Environment variables manage configuration.

The codebase mirrors the architecture: agent prompts and model creation are separated from graph state and nodes, while the MCP server and client live in a dedicated tool layer.

That separation makes the project easier to extend without coupling every agent directly to every external platform.”

## Slide 14 — Current Status, Limitations, and Roadmap

“Today, the working prototype includes both entry points, the four-node LangGraph workflow, the critic-repair loop, six MCP tools, live and mock adapters, targeted GitHub context, sandbox restrictions, RCA generation, Slack delivery, and multi-provider model selection.

There are also clear limitations.

It does not yet mutate the real repository or create a pull request. The webhook runs synchronously. Pinecone memory is not yet part of the active graph. The current default sandbox path gives its strongest real validation to Python syntax, while non-Python validation needs deeper language-specific execution.

The next milestones are therefore practical: connect episodic memory, add durable workers, run repairs in ephemeral containers, add a human approval gate, generate pull requests, improve observability and audit logs, and evaluate the system against a repeatable incident benchmark.”

## Slide 15 — Closing Vision

“The central idea behind Sentinel-Agent is simple:

Incident response should be an orchestrated engineering workflow, not a race across browser tabs.

This project demonstrates how specialized agents, targeted code context, protocol-isolated tools, bounded review loops, and verifiable outputs can work together as a foundation for safer AI-assisted operations.

Sentinel-Agent is not claiming to remove engineers from the process. It is designed to remove repetitive coordination, prepare a better-supported repair, and give the engineer a structured decision package.

Thank you. I’m happy to take your questions.”

## Optional 30-Second Elevator Pitch

“Sentinel-Agent is an agentic DevOps incident-response pipeline. It accepts an alert from a webhook or terminal, gathers GitHub, Datadog, repository, and Slack context through an MCP tool server, and routes the incident through four LangGraph agents: an SRE Analyst, Repair Engineer, Code Critic, and Sandbox Coordinator. The system iteratively reviews a proposed repair, validates it through restricted tools, and produces a structured RCA with Slack delivery. The result is a controlled, explainable path from incident detection to a review-ready engineering response.”

## Likely Questions and Suggested Answers

### Is this fully autonomous self-healing?

“It autonomously performs diagnosis, patch proposal, critic review, validation, and RCA generation. It deliberately does not commit or deploy the patch in the current prototype. A production version should introduce stronger sandboxing and a human approval gate before repository mutation.”

### Why use multiple agents instead of one prompt?

“The roles create separation of responsibility. The repair generator is not the final judge of its own output. The critic can reject the patch, preserve its reasoning as feedback, and trigger another attempt through a bounded graph transition.”

### Why use MCP?

“MCP gives the agents a consistent, explicit tool boundary. Integrations, credentials, filesystem controls, and execution rules remain in the tool server rather than being scattered through prompts or agent code.”

### How does the system avoid loading the whole repository?

“It retrieves only the suspected file, extracts its functions, searches for dependent files, and collects recent commits and diffs. This produces incident-specific context rather than a full-repository prompt.”

### What is real versus simulated?

“The agent graph, routing, MCP protocol calls, context assembly, patch generation, critic loop, RCA generation, and Python syntax validation are implemented. GitHub, Datadog, and Slack each support live and deterministic mock modes, depending on environment configuration.”

### Does the sandbox execute every generated patch?

“For Python targets, it compiles the generated patch text to verify syntax. The server also allow-lists pytest and TypeScript compile commands, but the active graph currently requests Python compile. For non-Python targets, the current default path is a lighter validation fallback, which is a known limitation.”

### Where is Pinecone used?

“The project contains a standalone episodic-memory module that can store resolved incidents and retrieve similar ones. It is implemented but not yet wired into the active LangGraph workflow. Connecting it before repair generation and after successful resolution is on the roadmap.”

### What would be required for production?

“Durable asynchronous workers, isolated container sandboxes, authentication and authorization, secret management, audit logging, human approval, repository mutation through pull requests, observability, and benchmark-based evaluation.”

