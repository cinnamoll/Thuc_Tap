from langgraph.graph import StateGraph, START, END
from typing import Literal 
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langgraph.types import interrupt
from pydantic import ValidationError

from Class.AgentState import AgentState
from Class.CleaningAction import CleaningAction, CleaningActionType
from Class.EDAInsight import EDAInsight
from Class.EngineeringAction import EngineeringAction, EncodingType, BinningType
from Subgraph.cleaning import cleaning
from Subgraph.eda import eda 
from Subgraph.feature import feature_engineering

@tool
def compute_impact_cleaning(action: CleaningAction, dataset_profile: dict) -> CleaningAction:
    """This tool compute risk level of cleaning action in a column

    Args:
        action (CleaningAction): Provide what type of cleaning action
        dataset_profile (dict): metadata about the column

    Returns:
        CleaningAction: Updated Cleaning action
    """
    total_rows = dataset_profile.get("n_rows") 

    if action.actionType == CleaningActionType.DROP_ROWS:
        affected = dataset_profile["stats"].get(f"{action.column}_nulls", 0)
    elif action.actionType == CleaningActionType.DROP_COLUMN:
        affected = total_rows 
    else:
        affected = 0  
    return {"rows_affected": affected, "rows_ratio": affected / total_rows if total_rows else 0.0}

@tool
def compute_impact_engineering(action: EngineeringAction, dataset_profile: dict) -> EngineeringAction:
    """This tool compute risk level of Encoding or Binning action in a column

    Args:
        action (CleaningAction): Provide what type of encoding / binning action
        dataset_profile (dict): metadata about the column

    Returns:
        CleaningAction: Updated Engineering action
    """
    total_rows = dataset_profile.get("n_rows") 
    null_count = dataset_profile["stats"].get(f"{action.column}_nulls", 0)

    if action.actionType in (EncodingType.LABEL, EncodingType.ORDINAL):
        affected = null_count
    elif action.actionType == EncodingType.ONE_HOT:
        affected = dataset_profile["stats"].get(f"{action.column}_nunique", 0)
    elif action.actionType in (BinningType.EQUAL, BinningType.QUANTILE): 
        affected = null_count  
    else:
        affected = 0
    return {"rows_affected": affected, "rows_ratio": affected / total_rows if total_rows else 0.0}

def compute_impact_node(state: AgentState) -> dict:
    dataset_profile = state.get('dataset_profile', {})
    calculated = []
    if state['action_type'] == 'cleaning':
        actions = state.get("pending_cleaning", [])
        for action in actions:
            impact = compute_impact_cleaning.invoke({"action": action, "dataset_profile": dataset_profile})
            calculated.append({"column": action.column, "actionType": action.actionType, **impact})
    elif state['action_type'] == 'engineering':
        actions = state.get("pending_engineer", [])
        for action in actions:
            impact = compute_impact_engineering.invoke({"action": action, "dataset_profile": dataset_profile})
            calculated.append({"column": action.column, "actionType": action.actionType, **impact})
    elif state['action_type'] == 'insight':  
        actions = state.get("pending_insight", []) 
        for action in actions: 
            calculated.append({"column": action.column, "actionType": "eda_insight", "rows_affected": 0, "rows_ratio": 0.0}) 

    return {"computed_impact": calculated}

def risk_node(state: AgentState) -> dict:
    computed_list = state.get("computed_impact", [])
    risk_levels = []
    
    for c in computed_list:
        pct = c.get("rows_ratio", 0.0)
        if pct < 0.05:
            risk_levels.append("low")
        elif pct < 0.20:
            risk_levels.append("medium")
        else:
            risk_levels.append("high")

    return {"risk_level": risk_levels}

def validator_node(state: AgentState) -> dict:
    computed_list = state.get("computed_impact", []) 
    if state['action_type'] == 'cleaning':
        actions = state.get('pending_cleaning', [])
    elif state['action_type'] == 'engineering':
        actions = state.get('pending_engineering', [])
    elif state['action_type'] == 'insight':  
        actions = state.get('pending_insight', []) 
    else: 
        actions = [] 
        
    for action in actions:
        try:
            type(action).model_validate(action.model_dump())
        except ValidationError:
            return {"validation": False, "validation_error": "schema_invalid"}

        if isinstance(action, EDAInsight): 
            continue 

        computed = next((c for c in computed_list if c["column"] == action.column and c["actionType"] == action.actionType), {})

        if action.rows_affected != computed.get("rows_affected", 0):
            return {
                "validation": False, 
                "validation_error": f"LLM reported {action.rows_affected} but system computed {computed.get('rows_affected', 0)} rows affected for {action.column}."
            }

    return {"validation": True, "validation_error": None}

def repair_node(state: AgentState) -> dict:
    error = state.get("validation_error", "Output has incorrect format or incorrect stats")
    retry_count = state.get("retry_count", 0) + 1
    repair_note = HumanMessage(content=(
        f"""Retry number: {retry_count} \t Last error: {error} 
            Recheck for correct format and stats to recommend a new action
        """
    ))
    return {"retry_count": retry_count, "messages": [repair_note]}

def human_review_node(state: AgentState) -> dict: 
    if state['action_type'] == 'cleaning':
        actions = state.get('pending_cleaning', [])
    elif state['action_type'] == 'engineering':
        actions = state.get('pending_engineering', [])
    elif state['action_type'] == 'insight':  
        actions = state.get('pending_insight', []) 
    else: 
        actions = [] 
        
    reviewed = list(state.get("reviewed_actions") or [])
    risk_levels = state.get("risk_level", [])
    
    target_action = None
    target_id = None
    for idx, action in enumerate(actions):
        act_type = getattr(action, "actionType", "eda_insight") 
        action_id = f"{action.column}_{act_type}"
        risk = risk_levels[idx] if idx < len(risk_levels) else "low"
        if risk == "high" and action_id not in reviewed:
            target_action = action
            target_id = action_id
            break

    if not target_action:
        return {"action_status": True, "reviewed_actions": reviewed, "pending_question": None}

    act_type = getattr(target_action, "actionType", "eda_insight") 
    rows_aff = getattr(target_action, "rows_affected", 0) 
    rows_rat = getattr(target_action, "rows_ratio", 0.0) 
    reason_str = getattr(target_action, "reason", f"EDA insight on {target_action.column}") 
    diff_summary = f"Action on {target_action.column} ({act_type}): affected {rows_aff} rows ({rows_rat}) due to {reason_str}\n"

    decision = interrupt({
        "type": "human_review_request",
        "action": target_action.model_dump(),
        "diff_summary": diff_summary,
        "dataset_preview": str(state.get('preview_feature', "")) if state['action_type'] == 'engineering' else ""
    })

    if not isinstance(decision, dict):
        return {
            "pending_question": f"Invalid decision payload for {target_id}",
            "reviewed_actions": reviewed
        }

    is_approved = decision.get("approved", False) or decision.get("decision") == "approve"
    if is_approved:
        reviewed.append(target_id)
        return {"action_status": True, "reviewed_actions": reviewed, "pending_question": None}
    else:
        return {"action_status": False, "reviewed_actions": reviewed, "pending_question": None}

def deterministic_fallback_node(state: AgentState):
    if state['action_type'] == 'cleaning':
        actions = state.get('pending_cleaning', [])
    elif state['action_type'] == 'engineering':
        actions = state.get('pending_engineering', [])
    elif state['action_type'] == 'insight':  
        actions = state.get('pending_insight', []) 
    else: 
        actions = [] 
    
    res = f"Dataset profile: {state.get('dataset_profile')}"    
    for action in actions:
        act_type = getattr(action, "actionType", "eda_insight") 
        rows_aff = getattr(action, "rows_affected", 0) 
        rows_rat = getattr(action, "rows_ratio", 0.0) 
        risk_lvl = getattr(action, "risk_level", "low") 
        res += f"""
            Univariate analysis on {action.column}: {state.get('univariate')}
            Action: {act_type}
            Rows affected: {rows_aff} (with ratio: {rows_rat})
            RISK LEVEL: {risk_lvl}
        """
        if state['action_type'] == 'engineering':
            res += f"Dataset preview: {state.get('preview_feature')}"
    return {"messages": [HumanMessage(content=res)], "fallback_used": True} 

def route_after_propose(state):
    pending = state.get("pending_insight", []) 
    if isinstance(pending, list) and len(pending) > 0: 
        return "validator" 
    return "compute_impact" 

def route_after_validator(state: AgentState) -> Literal["human_review", "repair", "__end__"]:
    if state.get("validation"):
        risk_levels = state.get("risk_level", [])
        if "high" in risk_levels:
            if state['action_type'] == 'cleaning':
                actions = state.get('pending_cleaning', [])
            elif state['action_type'] == 'engineering':
                actions = state.get('pending_engineering', [])
            elif state['action_type'] == 'insight': 
                actions = state.get('pending_insight', []) 
            else:
                actions = []
                
            reviewed = state.get("reviewed_actions") or []
            
            for action, risk in zip(actions, risk_levels):
                act_type = getattr(action, "actionType", "eda_insight") 
                action_id = f"{action.column}_{act_type}"
                if risk == "high" and action_id not in reviewed:
                    return "human_review"
            return END
        return END
    return "repair"

def route_after_human_review(state: AgentState) -> Literal["human_review", "__end__"]:
    if state.get("action_status") is False:
        return END

    if state['action_type'] == 'cleaning':
        actions = state.get('pending_cleaning', [])
    elif state['action_type'] == 'engineering':
        actions = state.get('pending_engineering', [])
    elif state['action_type'] == 'insight':  
        actions = state.get('pending_insight', []) 
    else: 
        actions = [] 

    risk_levels = state.get("risk_level", [])
    reviewed = state.get("reviewed_actions") or []
    
    for idx, action in enumerate(actions):
        act_type = getattr(action, "actionType", "eda_insight") 
        action_id = f"{action.column}_{act_type}"
        risk = risk_levels[idx] if idx < len(risk_levels) else "low"
        if risk == "high" and action_id not in reviewed:
            return "human_review"

    return END

def route_after_repair(state: AgentState) -> Literal["cleaning_graph", "feature_graph", "eda_graph", "deterministic_fallback"]: 
    if state.get("retry_count", 0) >= 3:
        return "deterministic_fallback"
    action_type = state.get('action_type')
    if action_type == 'cleaning':
        return "cleaning_graph"
    elif action_type == 'engineering':
        return "feature_graph"
    elif action_type == 'insight':  
        return "eda_graph" 
    return "deterministic_fallback"

validate_graph = StateGraph(AgentState)

validate_graph.add_node("compute_impact", compute_impact_node)
validate_graph.add_node("risk", risk_node)
validate_graph.add_node("validator", validator_node)
validate_graph.add_node("repair", repair_node)
validate_graph.add_node("deterministic_fallback", deterministic_fallback_node)
validate_graph.add_node("human_review", human_review_node)
validate_graph.add_node("cleaning_graph", cleaning) 
validate_graph.add_node("feature_graph", feature_engineering)
validate_graph.add_node("eda_graph", eda) 

validate_graph.add_edge(START, "compute_impact")
validate_graph.add_edge("compute_impact", "risk")
validate_graph.add_edge("risk", "validator")

validate_graph.add_conditional_edges(
    "validator",
    route_after_validator,
    {
        "human_review": "human_review",
        "repair": "repair",
        END: END,
    }
)

validate_graph.add_conditional_edges(
    "repair",
    route_after_repair,
    {
        "deterministic_fallback": "deterministic_fallback",
        "cleaning_graph":"cleaning_graph",
        "feature_graph":"feature_graph",
        "eda_graph":"eda_graph",
        END: END,
    }
)

validate_graph.add_edge("deterministic_fallback", END)

validate_graph.add_conditional_edges(
    "human_review",
    route_after_human_review,
    {
        "human_review": "human_review",
        END: END,
    }
)

validate_graph.add_edge("cleaning_graph", "compute_impact")
validate_graph.add_edge("feature_graph", "compute_impact")
validate_graph.add_edge("eda_graph", "compute_impact")  

validation = validate_graph.compile()

# img = validation.get_graph().draw_mermaid_png()
# with open('Subgraph_Img/validator_image.png', 'wb') as f:
#     f.write(img)