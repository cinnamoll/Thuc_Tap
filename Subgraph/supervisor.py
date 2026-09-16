from dotenv import load_dotenv
from langgraph.graph import END
from typing import TypedDict, Literal
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_deepseek import ChatDeepSeek
from langgraph.types import Command
import os
import json
import re
import uuid
from datetime import datetime

from Class.AgentState import AgentState

load_dotenv()
llm = ChatDeepSeek(model="deepseek-v4-flash")

class RouteDecision(TypedDict):
    next: Literal["cleaning", "eda", "feature_engineering", "ratio_trend_engine", "FINISH"]
    reason: str 

def parse_json_supervisor(raw_content: str) -> dict:
    text = raw_content.strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        text = match.group(0)
    try:
        return json.loads(text)
    except Exception:
        return {"next": "ratio_trend_engine", "reason": "Proceeding to ratio analysis"}

SUPERVISOR_PROMPT = """
    You are the Supervisor coordinating a data analysis pipeline. You MUST route tasks in strict graph sequence:
    `cleaning` -> `eda` -> `feature_engineering` -> `generate_report`

    **Sequential Order Rules:**
    1. Step 1: `cleaning` (Null handling, casting, OCR fix, unit standardization, identity reconciliation).
    2. Step 2: `eda` (Univariate Analysis, Trend Analysis, Common-Size Analysis, Charting, Cross-Statement Check).
    3. Step 3: `feature_engineering` (Standardization, growth rates, lag features, common-size transforms, cross-statement join).
    4. Step 4: `generate_report` (Generates the final comprehensive report).

    **Workflow Context:** 
    When you delegate to `cleaning`, `eda`, or `feature_engineering`, you trigger that pipeline stage.
    Their outputs will automatically flow through a downstream pipeline (`validation` -> `executor` -> `review`).
    After downstream execution completes, control returns to you to proceed to the next stage in sequence.

    Do not skip stages or terminate prematurely until all stages are complete.

    Respond with a JSON object matching this schema:
    {"next": "cleaning" | "eda" | "feature_engineering" | "generate_report" | "FINISH", "reason": "<string>"}
"""

def supervisor_core(state: AgentState):
    run_id = state.get('run_id', '') 
    if run_id == "": 
        run_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}" 

    # if state.get("analysis_mode") != "agent":
    #     return Command(
    #         goto="ratio_trend_engine",
    #         update={
    #             "run_id": run_id,
    #             "messages": [HumanMessage(content="[Supervisor] -> ratio_trend_engine (chế độ tất định)")],
    #         },
    #     )

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
        messages = [
            SystemMessage(content=SUPERVISOR_PROMPT),
            *state.get("messages", []),
            HumanMessage(content=(
                f"Metadata dataset:\n{state.get('metadata')}\n"
                f"Completed steps: {state.get('completed_actions', [])}\n" 
                "Proceed to next step"
            ))
        ]
        response = llm.invoke(messages)
        decision = parse_json_supervisor(getattr(response, "content", ""))
        goto = decision.get("next", "END")
        reason = decision.get("reason", "Proceeding to next step")

        if goto == "cleaning" and state.get("cleaning_done"):
            goto, reason = "ratio_trend_engine", "cleaning already done; proceeding to ratio analysis."
        elif goto == "eda" and state.get("eda_done"):
            goto, reason = "ratio_trend_engine", "eda already done; proceeding to ratio analysis."
        elif goto == "feature_engineering" and state.get("engineer_done"):
            goto, reason = "ratio_trend_engine", "feature_engineering already done; proceeding to ratio analysis."
    
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
    action_type = state.get("action_type")
    if not action_type:
        return "supervisor"
    pending = state.get(f"pending_{action_type}", [])
    if not pending:
        return "supervisor"
    last_action = pending[-1]
    act_type = getattr(last_action, "actionType", None)
    col = getattr(last_action, "column", "")
    act_type_str = str(getattr(act_type, "value", act_type)).lower()
    if str(col).lower() == "none" or act_type_str == "none":
        return "supervisor"
    return "executor"

def route_after_review(state: AgentState) -> Literal["executor", "validation", "supervisor"]:
    if state.get("review_decision", "") != "retry":
        return "supervisor"
    if state.get("retry_count", 0) >= 3:
        return "supervisor"      
    action = state.get('action_type')   
    if not action:
        return "supervisor"
    pending = state.get(f"pending_{action}", []) 
    current = state.get("current_action") 
    if pending and current and str(current) != str(pending[-1]): 
        return "validation"         
    return "executor"