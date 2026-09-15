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
    next: Literal["financial_validation", "cleaning", "eda", "feature_engineering", "financial_forecasting", "ratio_trend_engine", "FINISH"]
    reason: str 

SUPERVISOR_PROMPT = """
    You are the Supervisor coordinating a financial data analysis pipeline. You MUST route tasks in strict graph sequence:
    `financial_validation` -> `cleaning` -> `eda` -> `feature_engineering` -> `financial_forecasting` -> `generate_report`

    **Sequential Order Rules:**
    1. Step 1: `financial_validation` (Validate financial statement integrity and plausibility).
    2. Step 2: `cleaning` (Binning, encoding, null handling, casting, and data cleaning).
    3. Step 3: `eda` (Univariate Analysis, Multivariate Analysis, and Charting).
    4. Step 4: `feature_engineering` (Feature transformation, creation, encoding, and selection).
    5. Step 5: `financial_forecasting` (Predictive forecasting of financial metrics).
    6. Step 6: `generate_report` (Generates the final comprehensive report).

    **Workflow Context:**
    When you delegate to `financial_validation`, `cleaning`, `eda`, `feature_engineering`, or `financial_forecasting`, you trigger that pipeline stage.
    Their outputs will automatically flow through a downstream pipeline (`validation` -> `executor` -> `review` for cleaning/eda/feature_engineering).
    After downstream execution completes, control returns to you to proceed to the next stage in sequence.

    Do not skip stages or terminate prematurely until all stages are complete.

    Respond with a JSON object matching this schema:
    {"next": "financial_validation" | "cleaning" | "eda" | "feature_engineering" | "financial_forecasting" | "generate_report" | "FINISH", "reason": "<string>"}
"""

def supervisor_core(state: AgentState):
    run_id = state.get('run_id', '') 
    if run_id == "": 
        run_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}" 

    if state.get("analysis_mode") != "agent":
        return Command(
            goto="ratio_trend_engine",
            update={
                "run_id": run_id,
                "messages": [HumanMessage(content="[Supervisor] -> ratio_trend_engine (chế độ tất định)")],
            },
        )

    if not state.get("financial_validation_done"):
        goto = "financial_validation"
        reason = "Sequence rule: financial_validation step required first."
    elif not state.get("cleaning_done"):
        goto = "cleaning"
        reason = "Sequence rule: cleaning step required after financial_validation."
    elif not state.get("eda_done"):
        goto = "eda"
        reason = "Sequence rule: eda step required after cleaning."
    elif not state.get("engineer_done"):
        goto = "feature_engineering"
        reason = "Sequence rule: feature_engineering step required after eda."
    elif not state.get("financial_forecasting_done"):
        goto = "financial_forecasting"
        reason = "Sequence rule: financial_forecasting step required after feature_engineering."
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
        goto = decision.get("next", "END")
        reason = decision.get("reason", "Proceeding to next step")

        if goto == "financial_validation" and state.get("financial_validation_done"):
            goto, reason = "cleaning", "financial_validation already done; proceeding to cleaning."
        elif goto == "cleaning" and state.get("cleaning_done"):
            goto, reason = "eda", "cleaning already done; proceeding to eda."
        elif goto == "eda" and state.get("eda_done"):
            goto, reason = "feature_engineering", "eda already done; proceeding to feature_engineering."
        elif goto == "feature_engineering" and state.get("engineer_done"):
            goto, reason = "financial_forecasting", "feature_engineering already done; proceeding to financial_forecasting."
        elif goto == "financial_forecasting" and state.get("financial_forecasting_done"):
            goto, reason = "ratio_trend_engine", "financial_forecasting already done; proceeding to ratio analysis."
    
    if goto in ("FINISH", "generate_report", "END"):
        goto = "ratio_trend_engine"

    action_type = None
    if goto == "cleaning":
        action_type = "cleaning"
    elif goto == "feature_engineering":
        action_type = "engineering"
    elif goto == "eda":
        action_type = "insight"

    update_dict = {"run_id": run_id, "messages": [HumanMessage(content=f"[Supervisor] -> {goto}: {reason}")]}
    if action_type:
        update_dict["action_type"] = action_type

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