# AI Coder Context Structure

Excluded from this view: `.vscode/`, `__pycache__/`, `Omegavenv/`, and other generated or environment files.

```text
.
├── requirements.txt
├── run_pipeline.py
└── app/
    ├── __init__.py
    ├── config.py
    ├── main.py
    ├── Langgraph_agent_Orchestrator/
    │   ├── agents/
    │   │   ├── factory.py
    │   │   └── prompts.py
    │   ├── graph/
    │   │   ├── nodes.py
    │   │   ├── routers.py
    │   │   ├── state.py
    │   │   └── workflow.py
    │   └── memory/
    │       └── pinecone_vault.py
    └── The_Tools_Layer/
        ├── devops_mcp_server.py
        └── github_context_tool.py
```
