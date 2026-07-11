# run_pipeline.py
import logging
from app.config import settings  # Loads your .env variables safely
from app.Langgraph_agent_Orchestrator.graph.workflow import healing_pipeline_engine

# Setup clean terminal logging formatting
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

def main():
    print("=" * 60)
    print("🚀 SENTINEL-AGENT: AUTOMATED DEVOPS ORCHESTRATOR WORKSPACE")
    print("=" * 60)
    print("System is online. Ready to process terminal incident payloads.\n")

    # 1. Capture user inputs manually from terminal shell prompt
    incident_id = input("Enter Incident Tracking ID (e.g., INC-9921): ").strip()
    source_system = input("Enter Source System (github / datadog / slack): ").strip().lower()
    
    print("\nPaste your raw crash logs or stack trace below.")
    print("Enter 'EOF' on a new line when you are finished pasting:")
    
    log_lines = []
    while True:
        line = input()
        if line.strip() == "EOF":
            break
        log_lines.append(line)
    
    raw_logs = "\n".join(log_lines).strip()

    if not raw_logs:
        print("❌ Error: Crash log input cannot be empty. Exiting simulation.")
        return

    # 2. Package parameters into the initial LangGraph state dictionary contract
    initial_state = {
        "incident_id": incident_id if incident_id else "UNCATEGORIZED",
        "source_system": source_system if source_system in ["github", "datadog", "slack"] else "github",
        "raw_logs": raw_logs,
        "target_file": "",
        "commit_author": "",
        "priority_level": "",
        "proposed_patch": "",
        "critic_feedback": [],
        "critic_approved": False,
        "retry_counter": 0,
        "is_fixed": False,
        "final_rca_report": "",
        "incident_context": {},
        "repository_context": {},
        "slack_context": {},
        "sandbox_result": {},
        "slack_notification": {},
        "source_modes": {},
    }

    print("\n" + "[STATION CONTROL] Triggering LangGraph Self-Healing Engine..." + "\n")
    
    # 3. Invoke the execution flow loop execution track
    try:
        final_output_state = healing_pipeline_engine.invoke(initial_state)
        
        print("\n" + "=" * 60)
        print("🎯 PIPELINE RUN COMPLETED SUCCESSFULLY")
        print("=" * 60 + "\n")
        print(final_output_state.get("final_rca_report", "⚠️ No RCA report generated."))
        
    except Exception as e:
        print(f"\n❌ Pipeline Execution Crashed: {e}")

if __name__ == "__main__":
    main()
