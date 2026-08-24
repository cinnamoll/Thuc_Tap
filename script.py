from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from langchain_core.messages import HumanMessage
import uuid
import json
from datetime import datetime

from Class.FinancialState import FinancialReportState
from Subgraph.year_worker import year_worker_wrapper_node
from Subgraph.multi_year.dispatcher import file_dispatcher, route_to_year_workers, result_reducer
from Subgraph.multi_year.normalizer import schema_mapper, unit_currency_normalizer
from Subgraph.multi_year.accounting import accounting_identity_checker, yoy_variance_flagger
from Subgraph.multi_year.analysis import ratio_engine, trend_engine
from Subgraph.multi_year.reporting import (
    chart_composer, narrative_writer, generate_financial_report, build_financial_report
)

load_dotenv()

# ── generate_id node ──────────────────────────────────────────────────────────
def generate_id_node(state: FinancialReportState) -> dict:
    return {"run_id": f"fin_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"}

# ── Build Graph (section 3) ──────────────────────────────────────────────────
def build_financial_graph():
    workflow = StateGraph(FinancialReportState)

    # ── Register Nodes ────────────────────────────────────────────────────────
    workflow.add_node("generate_id", generate_id_node)
    workflow.add_node("file_dispatcher", file_dispatcher)            # Module 1
    workflow.add_node("year_worker", year_worker_wrapper_node)       # Subgraph (pipeline cũ)
    workflow.add_node("result_reducer", result_reducer)              # Module 1

    # Module 2
    workflow.add_node("schema_mapper", schema_mapper)
    workflow.add_node("unit_currency_normalizer", unit_currency_normalizer)

    # Module 3
    workflow.add_node("accounting_identity_checker", accounting_identity_checker)
    workflow.add_node("yoy_variance_flagger", yoy_variance_flagger)

    # Module 4
    workflow.add_node("ratio_engine", ratio_engine)
    workflow.add_node("trend_engine", trend_engine)

    # Module 5
    workflow.add_node("chart_composer", chart_composer)
    workflow.add_node("narrative_writer", narrative_writer)
    # Final report stage — node names kept identical to the design doc (part 3)
    # (`generate_report` -> `build_report`), implemented by the new multi-year nodes.
    workflow.add_node("generate_report", generate_financial_report)
    workflow.add_node("build_report", build_financial_report)

    # ── Edges & Routing ───────────────────────────────────────────────────────
    workflow.add_edge(START, "generate_id")
    workflow.add_edge("generate_id", "file_dispatcher")

    # Fan-Out: `file_dispatcher -->|Send x N năm| year_worker` (module 1)
    workflow.add_conditional_edges(
        "file_dispatcher",
        route_to_year_workers,
        ["year_worker"]
    )

    # Fan-In from year_worker to result_reducer
    workflow.add_edge("year_worker", "result_reducer")

    # Sequential Multi-Year Processing Steps
    workflow.add_edge("result_reducer", "schema_mapper")
    workflow.add_edge("schema_mapper", "unit_currency_normalizer")
    workflow.add_edge("unit_currency_normalizer", "accounting_identity_checker")
    workflow.add_edge("accounting_identity_checker", "yoy_variance_flagger")
    workflow.add_edge("yoy_variance_flagger", "ratio_engine")
    workflow.add_edge("ratio_engine", "trend_engine")
    workflow.add_edge("trend_engine", "chart_composer")
    workflow.add_edge("chart_composer", "narrative_writer")
    workflow.add_edge("narrative_writer", "generate_report")
    workflow.add_edge("generate_report", "build_report")
    workflow.add_edge("build_report", END)

    checkpointer = InMemorySaver()
    return workflow.compile(checkpointer=checkpointer)


app = build_financial_graph()

# img = app.get_graph().draw_mermaid_png()
# with open('graph_image.png', 'wb') as f:
#     f.write(img)

# ── CLI Runner ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    thread_config = {"configurable": {"thread_id": str(uuid.uuid4())}}

    print("═" * 60)
    print("  Multi-Year Financial Report Graph (Section 3)")
    print("═" * 60)
    print(f"Graph nodes: {list(app.get_graph().nodes.keys())}")
    print()

    def handle_stream(input_data):
        for event in app.stream(input_data, config=thread_config):
            for node_name, node_state in event.items():
                if node_name == "__interrupt__":
                    print("\nWorkflow Interrupted for Human Input")
                    continue
                print(f"\n Output from {node_name}")
                if isinstance(node_state, dict):
                    msgs = node_state.get('messages', [])  
                    if msgs: 
                        last_message = msgs[-1] 
                        content = getattr(last_message, 'content', None)
                        print(content if content else "[Tool Call / Output]") 
                    else: 
                        print(f"[{node_name}] Executed")

    while True:
        state_snapshot = app.get_state(thread_config)
        
        if state_snapshot.next and any(task.interrupts for task in state_snapshot.tasks):
            task = next(t for t in state_snapshot.tasks if t.interrupts)
            interrupt_val = task.interrupts[0].value
            
            print("\nINTERRUPT REQUIRED")
            if isinstance(interrupt_val, dict):
                print(json.dumps(interrupt_val, indent=2, ensure_ascii=False))
            else:
                print(f"Payload: {interrupt_val}")
            
            req_type = interrupt_val.get("type", "") if isinstance(interrupt_val, dict) else ""
            
            if req_type == "human_review_request":
                ans = input("Approve this action? (approve/reject or y/n): ").strip().lower()
                is_approved = ans in ["approve", "approved", "accept", "accepted", "y", "yes", "1"] or ans.startswith("y")
                decision = {"decision": "approve" if is_approved else "reject", "approved": is_approved}
            elif req_type == "confirm_action":
                ans = input("Enter decision (approve/reject/edit): ").strip().lower()
                if ans in ["y", "yes", "approve", "approved", "accept", "1"]:
                    ans_choice = "approve"
                elif ans in ["n", "no", "reject", "rejected", "0"]:
                    ans_choice = "reject"
                elif ans in ["edit"]:
                    ans_choice = "edit"
                else:
                    ans_choice = "approve"
                decision = {"decision": ans_choice, "new_action": []}
            elif req_type == "review_output":
                ans = input("Enter decision (approve/retry/abort): ").strip().lower()
                if ans in ["approve", "approved", "accept", "accepted", "y", "yes", "1"]:
                    ans_choice = "approve"
                elif ans in ["retry", "edit"]:
                    ans_choice = "retry"
                elif ans in ["abort", "reject", "no", "n", "0"]:
                    ans_choice = "abort"
                else:
                    ans_choice = "approve"
                decision = {"decision": ans_choice}
            else:
                ans = input("Enter resume response (approve/reject or y/n): ").strip().lower()
                is_approved = ans in ["approve", "approved", "accept", "accepted", "y", "yes", "1"] or ans.startswith("y")
                decision = {"decision": "approve" if is_approved else "reject", "approved": is_approved}

            print(f"Resuming graph with Command(resume={decision})")
            handle_stream(Command(resume=decision))
        else:
            user_input = input("\nEnter CSV file paths (comma-separated) or 'exit': ").strip()
            if user_input.lower() == 'exit':
                break
            if not user_input:
                continue
            
            # Parse input: comma-separated file paths
            input_files = [f.strip() for f in user_input.split(",") if f.strip()]
            handle_stream({"input_files": input_files})