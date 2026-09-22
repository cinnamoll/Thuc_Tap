import json
import uuid
from dotenv import load_dotenv
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, Send

from Class.FinancialState import FinancialReportState
from Subgraph.accounting_checks import accounting_check_node
from Subgraph.code_mapping import canonicalize_metrics
from Subgraph.charts import build_charts_node
from Subgraph.cross_check import cross_check_scope_node
from Subgraph.extraction import extraction_worker_node
from Subgraph.harmonizer import schema_harmonizer_node
from Subgraph.indexing import build_batch_node, index_files_node, select_files_node
from Subgraph.materialize import materialize_node
from Subgraph.financial_validation import financial_validation_node
from Subgraph.financial_forecasting import financial_forecasting_node
from Subgraph.ratio_trend import ratio_trend_engine
from Subgraph.report.reporting import build_report_node, generate_report_node, review_report_node, route_after_report_review
from Subgraph.report.feedback import interpret_feedback_node, route_feedback_node

VALID_APPROVE_CHOICES = {"approve", "approved", "accept", "accepted", "y", "yes", "1"}
VALID_RETRY_CHOICES = {"retry", "edit", "redo", "again"}
VALID_ABORT_CHOICES = {"abort", "reject", "no", "n", "0", "cancel", "stop"}

load_dotenv()

def route_to_extraction_workers(state: FinancialReportState) -> list:
    plan = state.get("extraction_plan") or []
    return [Send("extraction_worker", item) for item in plan]

def is_pdf_input_path(user_text: str) -> bool:
    text = user_text.lower()
    return ".pdf" in text or ("/" in user_text and "," in user_text)

graph = StateGraph(FinancialReportState)

graph.add_node("generate_batch_id", build_batch_node)
graph.add_node("index_files_node", index_files_node)
graph.add_node("select_files_node", select_files_node)
graph.add_node("extraction_worker", extraction_worker_node)

graph.add_node("schema_harmonizer_node", schema_harmonizer_node)
graph.add_node("materialize_node", materialize_node)
graph.add_node("canonicalize_metrics", canonicalize_metrics)

graph.add_node("financial_validation", financial_validation_node)
graph.add_node("accounting_check", accounting_check_node)
graph.add_node("cross_check_scope_node", cross_check_scope_node)
graph.add_node("financial_forecasting", financial_forecasting_node)

graph.add_node("ratio_trend_engine", ratio_trend_engine)
graph.add_node("financial_charts", build_charts_node)
graph.add_node("generate_report", generate_report_node)
graph.add_node("review_report", review_report_node)
graph.add_node("interpret_feedback", interpret_feedback_node)
graph.add_node("route_feedback", route_feedback_node)
graph.add_node("build_report", build_report_node)

graph.add_edge(START, "generate_batch_id")
graph.add_edge("generate_batch_id", "index_files_node")
graph.add_edge("index_files_node", "select_files_node")
graph.add_conditional_edges("select_files_node", route_to_extraction_workers, ["extraction_worker"])
graph.add_edge("extraction_worker", "schema_harmonizer_node")
graph.add_edge("schema_harmonizer_node", "materialize_node")
graph.add_edge("materialize_node", "canonicalize_metrics")
graph.add_edge("canonicalize_metrics", "financial_validation")
graph.add_edge("financial_validation", "cross_check_scope_node")
graph.add_edge("cross_check_scope_node", "financial_forecasting")
graph.add_edge("financial_forecasting", "accounting_check")
graph.add_edge("accounting_check", "ratio_trend_engine")
graph.add_edge("ratio_trend_engine", "financial_charts")
graph.add_edge("financial_charts", "generate_report")
graph.add_edge("generate_report", "review_report")
graph.add_conditional_edges(
    "review_report",
    route_after_report_review,
    {
        "build_report": "build_report", 
        "interpret_feedback": "interpret_feedback", 
        "end": END
    }
)
graph.add_edge("interpret_feedback", "route_feedback")
graph.add_edge("build_report", END)

checkpointer = InMemorySaver()
app = graph.compile(checkpointer=checkpointer)

if __name__ == "__main__":
    thread_config = {"configurable": {"thread_id": str(uuid.uuid4())}}

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

            if req_type == "review_output":
                start_new_batch = False
                ans_choice = "approve"
                rejection_reason = None
                new_input_files = None

                while True:
                    ans = input("Enter decision (approve/retry/abort) or 'new' to start new batch: ").strip()
                    if not ans:
                        print("Chưa nhập lựa chọn. Vui lòng nhập 'approve', 'retry', 'abort' hoặc 'new':")
                        continue
                    if is_pdf_input_path(ans) or ans.lower() == "new":
                        start_new_batch = True
                        if is_pdf_input_path(ans):
                            new_input_files = [f.strip() for f in ans.split(",") if f.strip()]
                        break

                    ans_lower = ans.lower()
                    if ans_lower in VALID_APPROVE_CHOICES:
                        ans_choice = "approve"
                        break
                    elif ans_lower in VALID_RETRY_CHOICES:
                        ans_choice = "retry"
                        break
                    elif ans_lower in VALID_ABORT_CHOICES:
                        ans_choice = "abort"
                        break
                    else:
                        print("Lựa chọn không hợp lệ. Vui lòng nhập 'approve', 'retry', 'abort' hoặc 'new'.")

                if start_new_batch:
                    print("\nHủy luồng cũ, khởi tạo luồng phân tích mới...")
                    thread_config = {"configurable": {"thread_id": str(uuid.uuid4())}}
                    if not new_input_files:
                        user_input = input("\nEnter PDF file paths (comma-separated) or 'exit': ").strip()
                        if user_input.lower() == "exit":
                            break
                        if not user_input:
                            continue
                        new_input_files = [f.strip() for f in user_input.split(",") if f.strip()]
                    handle_stream({"input_files": new_input_files})
                    continue

                if ans_choice == "retry":
                    rejection_reason = input("Nhập lý do từ chối / cần sửa đổi (rejection reason): ").strip()
                decision = {"decision": ans_choice, "rejection_reason": rejection_reason}

                print(f"Resuming graph with Command(resume={decision})")
                handle_stream(Command(resume=decision))
            else:
                start_new_batch = False
                decision = None
                new_input_files = None

                while True:
                    ans = input("Enter decision (approve/reject) or 'new' to start new batch: ").strip()
                    if not ans:
                        print("Chưa nhập lựa chọn. Vui lòng nhập (approve/reject/new):")
                        continue
                    if is_pdf_input_path(ans) or ans.lower() == "new":
                        start_new_batch = True
                        if is_pdf_input_path(ans):
                            new_input_files = [f.strip() for f in ans.split(",") if f.strip()]
                        break

                    ans_lower = ans.lower()
                    if ans_lower in VALID_APPROVE_CHOICES:
                        decision = {"decision": "approve", "approved": True}
                        break
                    elif ans_lower in VALID_ABORT_CHOICES:
                        decision = {"decision": "reject", "approved": False}
                        break
                    else:
                        print("Lựa chọn không hợp lệ. Vui lòng nhập 'approve', 'reject' hoặc 'new'.")

                if start_new_batch:
                    print("\nHủy luồng cũ, khởi tạo luồng phân tích mới...")
                    thread_config = {"configurable": {"thread_id": str(uuid.uuid4())}}
                    if not new_input_files:
                        user_input = input("\nEnter PDF file path or 'exit': ").strip()
                        if user_input.lower() == "exit":
                            break
                        if not user_input:
                            continue
                        new_input_files = [f.strip() for f in user_input.split(",") if f.strip()]
                    if new_input_files:
                        handle_stream({"input_files": new_input_files})
                    continue

                if decision is not None:
                    print(f"Resuming graph with Command(resume={decision})")
                    handle_stream(Command(resume=decision))
        else:
            user_input = input("\nEnter PDF file path or 'exit': ").strip()
            if user_input.lower() == "exit":
                break
            if not user_input:
                continue
            input_files = [f.strip() for f in user_input.split(",") if f.strip()]
            thread_config = {"configurable": {"thread_id": str(uuid.uuid4())}}
            handle_stream({"input_files": input_files})