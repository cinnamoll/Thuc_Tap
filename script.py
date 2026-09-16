import json
import uuid
from dotenv import load_dotenv
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, Send

from Class.FinancialState import FinancialReportState
# from Subgraph.accounting_checks import run_accounting_checks
from Subgraph.code_mapping import canonicalize_metrics
from Subgraph.charts import build_charts_node
from Subgraph.cleaning import cleaning
from Subgraph.cross_check import cross_check_scope
from Subgraph.eda import eda
from Subgraph.executor import executor_node, review_execution_node
from Subgraph.extraction import extraction_worker_node
from Subgraph.feature import feature_engineering
from Subgraph.harmonizer import schema_harmonizer
from Subgraph.indexing import build_batch, index_files, select_files
from Subgraph.materialize import materialize_dataset
from Subgraph.financial_validation import financial_validation_node
from Subgraph.financial_forecasting import financial_forecasting_node
from Subgraph.scenario_analysis import scenario_analysis_node
from Subgraph.ratio_trend import ratio_trend_engine
from Subgraph.reporting import build_report_node, generate_report_node, review_report_node, route_after_report_review
from Subgraph.supervisor import route_after_review, route_after_validation, supervisor_core
from Subgraph.validator import validation

load_dotenv()

def route_to_extraction_workers(state: FinancialReportState) -> list:
    plan = state.get("extraction_plan") or []
    return [Send("extraction_worker", item) for item in plan]

graph = StateGraph(FinancialReportState)

graph.add_node("generate_batch_id", build_batch)
graph.add_node("index_files", index_files)
graph.add_node("select_files", select_files)
graph.add_node("extraction_worker", extraction_worker_node)

graph.add_node("schema_harmonizer", schema_harmonizer)
graph.add_node("materialize_dataset", materialize_dataset)
graph.add_node("canonicalize_metrics", canonicalize_metrics)

graph.add_node("financial_validation", financial_validation_node)
graph.add_node("cross_check_scope", cross_check_scope)
graph.add_node("financial_forecasting", financial_forecasting_node)
graph.add_node("scenario_analysis", scenario_analysis_node)

graph.add_node("supervisor", supervisor_core)
graph.add_node("cleaning", cleaning)
graph.add_node("eda", eda)
graph.add_node("feature_engineering", feature_engineering)
graph.add_node("validation", validation)
graph.add_node("executor", executor_node)
graph.add_node("review", review_execution_node)

graph.add_node("ratio_trend_engine", ratio_trend_engine)
graph.add_node("financial_charts", build_charts_node)
graph.add_node("generate_report", generate_report_node)
graph.add_node("review_report", review_report_node)
graph.add_node("build_report", build_report_node)

graph.add_edge(START, "generate_batch_id")
graph.add_edge("generate_batch_id", "index_files")
graph.add_edge("index_files", "select_files")
graph.add_conditional_edges("select_files", route_to_extraction_workers, ["extraction_worker"])
graph.add_edge("extraction_worker", "schema_harmonizer")
graph.add_edge("schema_harmonizer", "materialize_dataset")
graph.add_edge("materialize_dataset", "canonicalize_metrics")
graph.add_edge("canonicalize_metrics", "financial_validation")
graph.add_edge("financial_validation", "cross_check_scope")
graph.add_edge("cross_check_scope", "financial_forecasting")
graph.add_edge("financial_forecasting", "scenario_analysis")
graph.add_edge("scenario_analysis", "supervisor")

graph.add_edge("cleaning", "validation")
graph.add_edge("eda", "validation")
graph.add_edge("feature_engineering", "validation")
graph.add_conditional_edges(
    "validation",
    route_after_validation,
    {
        "executor": "executor", 
        "supervisor": "supervisor"
    }
)
graph.add_edge("executor", "review")
graph.add_conditional_edges(
    "review",
    route_after_review,
    {
        "executor": "executor", 
        "validation": "validation", 
        "supervisor": "supervisor"
    }
)

graph.add_edge("ratio_trend_engine", "financial_charts")
graph.add_edge("financial_charts", "generate_report")
graph.add_edge("generate_report", "review_report")
graph.add_conditional_edges(
    "review_report",
    route_after_report_review,
    {
        "build_report": "build_report", 
        "generate_report": "generate_report", 
        "end": END
    }
)
graph.add_edge("build_report", END)

checkpointer = InMemorySaver()
app = graph.compile(checkpointer=checkpointer)

if __name__ == "__main__":
    thread_config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    # print("  Batch PDF Financial Report Pipeline")
    # print(f"  nodes: {sorted(graph.nodes)}")

    def handle_stream(input_data):
        for event in app.stream(input_data, config=thread_config):
            for node_name, node_state in event.items():
                if node_name == "__interrupt__":
                    print("\nWorkflow Interrupted")
                    continue
                print(f"\n Output from {node_name}")
                if isinstance(node_state, dict):
                    msgs = node_state.get("messages", [])
                    if msgs:
                        last_message = msgs[-1]
                        content = getattr(last_message, "content", None)
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
                elif ans == "edit":
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
            user_input = input("\nEnter PDF file paths (comma-separated) or 'exit': ").strip()
            if user_input.lower() == "exit":
                break
            if not user_input:
                continue
            input_files = [f.strip() for f in user_input.split(",") if f.strip()]
            thread_config = {"configurable": {"thread_id": str(uuid.uuid4())}}
            handle_stream({"input_files": input_files, "analysis_mode": "agent"})