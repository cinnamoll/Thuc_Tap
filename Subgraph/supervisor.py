from dotenv import load_dotenv
from langgraph.graph import END
from typing import TypedDict, Literal
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_deepseek import ChatDeepSeek
from langgraph.types import Command
import uuid
from datetime import datetime

from Class.AgentState import AgentState

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


def _supervisor_core(state: AgentState, final_goto: str):
    """
    Shared supervisor decision logic.

    Parameters
    ----------
    state : AgentState
    final_goto : str
        The node name to route to once all three stages (cleaning, eda,
        feature_engineering) are complete.  For the standalone pipeline this
        is ``"generate_report"``; for the year-worker subgraph this is
        ``"__end__"`` (i.e. `END`).
    """
    check = state.get('check_start', True)
    run_id = state.get('run_id', '') 
    if check == True: 
        run_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}" 

    # Enforce graph sequence: cleaning -> eda -> feature_engineering -> final
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
        goto = decision.get("next", final_goto)
        reason = decision.get("reason", "Proceeding to next step")

        # Enforce sequence: never let the LLM re-route to a stage that is already done,
        # otherwise the pipeline can loop forever re-running completed subgraphs.
        if goto == "cleaning" and state.get("cleaning_done"):
            goto, reason = final_goto, "cleaning already done; forcing final stage."
        elif goto == "eda" and state.get("eda_done"):
            goto, reason = final_goto, "eda already done; forcing final stage."
        elif goto == "feature_engineering" and state.get("engineer_done"):
            goto, reason = final_goto, "feature_engineering already done; forcing final stage."
    
    if goto == "FINISH":
        goto = END

    # Map goto -> action_type for downstream nodes
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

    return goto, update_dict


def supervisor_node(state: AgentState) -> Command[Literal["cleaning", "eda", "feature_engineering", "generate_report", "__end__"]]:
    """Supervisor for the standalone single-file pipeline (script.py)."""
    goto, update_dict = _supervisor_core(state, final_goto="generate_report")
    return Command(goto=goto, update=update_dict)


def supervisor_node_subgraph(state: AgentState) -> Command[Literal["cleaning", "eda", "feature_engineering", "__end__"]]:
    """
    Supervisor for the year_worker subgraph.
    
    When all stages are done it routes to __end__ instead of generate_report,
    because generate_report lives in the top-level financial graph (not inside
    the per-year subgraph).
    """
    goto, update_dict = _supervisor_core(state, final_goto=END)
    return Command(goto=goto, update=update_dict)


def route_after_validation(state: AgentState) -> Literal["executor", "supervisor"]:
    if state.get("action_status") is False:
        return "supervisor"
    return "executor"


def route_after_review(state: AgentState) -> Literal["executor", "validation", "supervisor"]:
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
