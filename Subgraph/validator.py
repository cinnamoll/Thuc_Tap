from langgraph.graph import StateGraph, START, END
from typing import Literal, Dict
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langgraph.types import interrupt
from pydantic import ValidationError

from Class.AgentState import AgentState
from Subgraph.cleaning import CleaningAction, CleaningActionType, cleaning_graph, cleaning
from Subgraph.eda import EDAInsight
from Subgraph.feature import EngineeringAction, EncodingType, BinningType, feature_graph, feature_engineering

@tool
def compute_impact_cleaning(action: CleaningAction, dataset_profile: Dict) -> CleaningAction:
    """This tool compute risk level of cleaning action in a column

    Args:
        action (CleaningAction): Provide what type of cleaning action
        dataset_profile (Dict): metadata about the column

    Returns:
        CleaningAction: Updated Cleaning action
    """
    stats = dataset_profile["stats"]
    total_rows = dataset_profile.get("n_rows") 

    if action.actionType == CleaningActionType.DROP_ROWS:
        affected = stats.get(f"{action.column}_nulls", 0)
    elif action.actionType == CleaningActionType.DROP_COLUMN:
        affected = total_rows 
    else:
        affected = 0  

    action.rows_affected = affected
    action.rows_ratio = affected / total_rows if total_rows else 0.0
    return action

@tool
def compute_impact_engineering(action: EngineeringAction, dataset_profile: Dict) -> EngineeringAction:
    """This tool compute risk level of Encoding or Binning action in a column

    Args:
        action (CleaningAction): Provide what type of encoding / binning action
        dataset_profile (Dict): metadata about the column

    Returns:
        CleaningAction: Updated Engineering action
    """
    total_rows = dataset_profile.get("n_rows") 
    null_count = dataset_profile["stats"].get(f"{action.column}_nulls", 0)

    if action.actionType in (EncodingType.LABEL, EncodingType.ORDINAL):
        affected = null_count
    elif action.actionType == EncodingType.ONE_HOT:
        affected = dataset_profile["stats"].get(f"{action.column}_nunique", 0)
    elif action.actionType in (BinningType.EQUAL_WIDTH, BinningType.QUANTILE):
        affected = null_count  
    else:
        affected = 0

    action.rows_affected = affected
    action.rows_ratio = affected / total_rows if total_rows else 0.0
    return action

def compute_impact_node(state: AgentState) -> Dict:
    action = state["pending_action"]
    dataset_profile = state['dataset_profile']

    if isinstance(action, CleaningAction):
        calculated = compute_impact_cleaning.invoke(action, dataset_profile)
    else:
        calculated = compute_impact_engineering.invoke(action, dataset_profile)

    return {
        "pending_action": calculated, 
        "computed_impact": {"rows_affected": calculated.rows_affected, "rows_ratio": calculated.rows_ratio}
    }

def risk_node(state: AgentState) -> Dict:
    pct = state.get("computed_impact", {}).get("rows_ratio", 0.0)

    if pct < 0.05:
        risk_level = "low"
    elif pct < 0.20:
        risk_level = "medium"
    else:
        risk_level = "high"

    return {"risk_level": risk_level}

def validator_node(state: AgentState) -> Dict:
    action = state["pending_action"]
    computed = state.get("computed_impact", {}) 
       
    try:
        type(action).model_validate(action.model_dump())
    except ValidationError:
        return {"validation": False, "validation_error": "schema_invalid"}

    if action.rows_affected != computed.get("rows_affected", 0):
        return {
            "validation": False, 
            "validation_error": f"LLM reported {action.rows_affected} but system computed {computed.get('rows_affected')} rows affected."
        }

    return {"validation": True, "validation_error": None}

def repair_node(state: AgentState) -> Dict:
    error = state.get("validation_error", "Output has incorrect format or incorrect stats")
    retry_count = state.get("retry_count", 0) + 1

    repair_note = HumanMessage(
        content=(f"""
            Retry number: {retry_count}
            Last error: {error}
            Recheck for correct format and stats to recommend a new action
        """))

    return {"retry_count": retry_count, "messages": [repair_note]}

def human_review_node(state: AgentState) -> Dict:
    action = state["pending_action"]

    diff_summary = f"Will drop {action.rows_affected} rows ({action.rows_ratio}) due to {action.reason}"

    decision = interrupt({
        "type": "human_review_request",
        "action": action.model_dump(),
        "diff_summary": diff_summary,
    })

    if decision.get("approved"):
        return {"action_status": True}

    return {"action_status": False, "pending_action": None}

def deterministic_fallback_node(state: AgentState):
    action = state['pending_action']
    res = f"""
        Dataset profile: {state['dataset_profile']}
        Univariate analysis on {action.column}: {state['univariate']}
        Action: {action.actionType}
        Rows affected: {action.rows_affected} (with ratio: {action.rows_ratio})
        RISK LEVEL: {action.risk_level}
    """
    return {"messages": HumanMessage(res), "fallback_used": True}

def route_after_propose(state):
    if isinstance(state.get("pending_output"), EDAInsight):
        return "validator" 
    return "compute_impact"  

def route_after_validator(state: AgentState) -> Literal["human_review", "repair", "__end__"]:
    if state.get("validation"):
        if state.get("risk_level") == "high":
            return "human_review"
        return END
    return "repair"

def route_after_repair(state: AgentState) -> Literal["cleaning_graph", "feature_graph", "deterministic_fallback"]:
    if state.get("retry_count", 0) >= 3:
        return "deterministic_fallback"

    action = state["pending_action"]
    if isinstance(action, CleaningAction):
        return "cleaning_graph"
    elif isinstance(action, EngineeringAction):
        return "feature_graph"

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
        END: END,
    }
)

validate_graph.add_edge("deterministic_fallback", END)
validate_graph.add_edge("human_review", END)

validate_graph.add_edge("cleaning_graph", "compute_impact")
validate_graph.add_edge("feature_graph", "compute_impact")

validation = validate_graph.compile()

# img = validation.get_graph().draw_mermaid_png()
# with open('Subgraph_Img/validator_image.png', 'wb') as f:
#     f.write(img)