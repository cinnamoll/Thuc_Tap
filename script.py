from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from typing import List, TypedDict, Literal
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from langchain_deepseek import ChatDeepSeek
from langgraph.types import Command
import uuid
from datetime import datetime
from langgraph.checkpoint.memory import InMemorySaver
import json

from Class.AgentState import AgentState
from Subgraph.eda import eda
from Subgraph.cleaning import cleaning
from Subgraph.feature import feature_engineering
from Subgraph.validator import validation
from Subgraph.executor import executor_node, review_execution_node
from Subgraph.report import generate_report_node, build_report_file_node

load_dotenv()

llm = ChatDeepSeek(model="deepseek-v4-flash")

class RouteDecision(TypedDict):
    next: Literal["cleaning", "eda", "feature_engineering", "review", "generate_report", "FINISH"]
    reason: str 

SUPERVISOR_PROMPT = """
    You are the Supervisor coordinating a data analysis pipeline. You MUST route tasks in strict graph sequence:
    `cleaning` -> `eda` -> `feature_engineering` -> `generate_report`

    **Sequential Order Rules:**
    1. Step 1: `cleaning` (Binning, encoding, null handling, casting, and data cleaning).
    2. Step 2: `eda` (Univariate Analysis, Multivariate Analysis, and Charting).
    3. Step 3: `feature_engineering` (Feature transformation, creation, encoding, and selection).
    4. Step 4: `generate_report` (Generates the final comprehensive report).

    **Workflow Context:** 
    When you delegate to `cleaning`, `eda`, or `feature_engineering`, you trigger that pipeline stage.
    Their outputs will automatically flow through a downstream pipeline (`validation` -> `executor` -> `review`).
    After downstream execution completes, control returns to you to proceed to the next stage in sequence.

    Do not skip stages or terminate prematurely until all stages are complete.

    Respond with a JSON object matching this schema:
    {"next": "cleaning" | "eda" | "feature_engineering" | "generate_report" | "FINISH", "reason": "<string>"}
"""

def supervisor_node(state: AgentState) -> Command[Literal["cleaning", "eda", "feature_engineering", "generate_report", "__end__"]]:
    check = state.get('check_start', True)
    run_id = state.get('run_id', '') 
    if check == True: 
        run_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}" 

    # Enforce graph sequence: cleaning -> eda -> feature_engineering -> generate_report
    if not state.get("cleaning_done"):
        goto = "cleaning"
        reason = "Sequence rule: cleaning step required first."
    elif not state.get("eda_done"):
        goto = "eda"
        reason = "Sequence rule: eda step required after cleaning."
    elif not state.get("engineer_done"):
        goto = "feature_engineering"
        reason = "Sequence rule: feature_engineering step required after eda."
    else:
        llm_router = llm.with_structured_output(RouteDecision, method='json_mode')
        messages = [
            SystemMessage(content=SUPERVISOR_PROMPT),
            *state.get("messages", []),
            HumanMessage(content=(
                f"Metadata dataset:\n{state.get('metadata')}\n"
                f"Completed steps: {state.get('completed_actions', [])}\n" 
                "Proceed to next step"
            ))
        ]
        decision = llm_router.invoke(messages)
        goto = decision.get("next", "generate_report")
        reason = decision.get("reason", "Proceeding to next step")

        # Enforce sequence: never let the LLM re-route to a stage that is already done,
        # otherwise the pipeline can loop forever re-running completed subgraphs.
        if goto == "cleaning" and state.get("cleaning_done"):
            goto, reason = "generate_report", "cleaning already done; forcing report stage."
        elif goto == "eda" and state.get("eda_done"):
            goto, reason = "generate_report", "eda already done; forcing report stage."
        elif goto == "feature_engineering" and state.get("engineer_done"):
            goto, reason = "generate_report", "feature_engineering already done; forcing report stage."
    
    if goto == "FINISH":
        goto = END

    action_type = None
    if goto == "cleaning":
        action_type = "cleaning"
    elif goto == "feature_engineering":
        action_type = "engineering"
    elif goto == "eda":
        action_type = "insight"

    update_dict = {  
        "run_id": run_id, 
        "check_start": False, 
        "messages": [HumanMessage(content=f"[Supervisor] -> {goto}: {reason}")],
    }
    if action_type:
        update_dict["action_type"] = action_type

    return Command(
        goto=goto,
        update=update_dict,
    )
    
def route_after_review(state:AgentState) -> Literal["executor", "validation", "supervisor"]:
    if state.get("review_decision", "") != "retry":
        return "supervisor"
    if state.get("retry_count", 0) >= 3:
        return "supervisor"      
    action = state['action_type']   
    pending = state.get(f"pending_{action}", []) 
    current = state.get("current_action") 
    if pending and current and str(current) != str(pending[-1]): 
        return "validation"         
    return "executor"   

checkpointer = InMemorySaver()
thread_config = {"configurable":{"thread_id": uuid.uuid4()}}

graph = StateGraph(AgentState)

graph.add_node('supervisor', supervisor_node)
graph.add_node('cleaning', cleaning)
graph.add_node('eda', eda)
graph.add_node('feature_engineering', feature_engineering)
graph.add_node('validation', validation)
graph.add_node('executor', executor_node)
graph.add_node("review", review_execution_node)
graph.add_node('generate_report', generate_report_node)
graph.add_node('build_report', build_report_file_node)

def route_after_validation(state: AgentState) -> Literal["executor", "supervisor"]:
    if state.get("action_status") is False:
        return "supervisor"
    return "executor"

graph.add_edge(START, 'supervisor')
# graph.add_edge('supervisor', 'cleaning')
# graph.add_edge('supervisor', 'eda')
# graph.add_edge('supervisor', 'feature_engineering')
graph.add_edge('cleaning', 'validation')
graph.add_edge('eda', 'validation')
graph.add_edge('feature_engineering', 'validation')

graph.add_conditional_edges(
    "validation",
    route_after_validation,
    {
        "executor": "executor",
        "supervisor": "supervisor",
    },
)

graph.add_edge("executor", "review")
graph.add_edge("generate_report", "build_report")
graph.add_edge("build_report", END)

graph.add_conditional_edges(
    "review",
    route_after_review,
    {
        "executor": "executor",
        "validation": "validation",
        "supervisor": "supervisor",
    },
)

app = graph.compile(checkpointer=checkpointer)

# img = app.get_graph().draw_mermaid_png()
# with open('graph_image.png', 'wb') as f:
#     f.write(img)

if __name__ == "__main__":
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
            user_input = input("\nEnter prompt (or 'exit' to quit): ").strip()
            if user_input.lower() == 'exit':
                break
            if not user_input:
                continue
            
            handle_stream({'messages': [HumanMessage(content=user_input)]})