from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, START, END
from typing import Literal
from langchain_core.tools import tool
import polars as pl
from langgraph.types import interrupt
import logging

from Class.AgentState import AgentState
from cleaning import CleaningAction, CleaningActionType
from feature import EngineeringAction, EncodingType, BinningType

logger = logging.getLogger(__name__)

@tool
def apply_cleaning_tool(action: CleaningAction, skip_confirm: bool, output_path: str) -> str:
    """
    Apply a specific cleaning action to a column of the dataset and write the results to a new file.
    Only call this tool after clearly identifying the problem via profile_dataset.
    This tool will pause and wait for user confirmation before actually overwriting the data.
    """
    if not skip_confirm:
        decision = interrupt({
            "type": "confirm_cleaning",
            "column": action.column,
            "action": action.actionType,
            "message": f"Use'{action.actionType}' on '{action.column}'? (approve/reject/edit)",
        })

        if decision.get("decision") == "reject":
            return f"Cancel '{action}' on '{action.column}'"

    lf = pl.scan_file(action.file_path, action.file_format)

    if action.actionType == CleaningActionType.DROP_ROWS:
        lf = lf.drop_nulls(subset=[action.column])
    elif action.actionType == CleaningActionType.IMPUTE_MEDIAN:
        lf = lf.with_columns(pl.col(action.column).fill_null(pl.col(action.column).median()))
    elif action.actionType == CleaningActionType.IMPUTE_MEAN:
        lf = lf.with_columns(pl.col(action.column).fill_null(pl.col(action.column).mean()))
    elif action.actionType == CleaningActionType.IMPUTE_MODE:
        lf = lf.with_columns(pl.col(action.column).fill_null(pl.col(action.column).mode().first()))
    elif action.actionType == CleaningActionType.CAST_DTYPE:
        lf = lf.with_columns(pl.col(action.column).cast(getattr(pl, action.target_dtype)))
    elif action.actionType == CleaningActionType.DROP_COLUMN:
        lf = lf.drop(action.column)

    lf.sink_csv(output_path) 
    return f"Use '{action}' on '{action.column}', save at {output_path}"

@tool
def encoding_tool(action: EngineeringAction, skip_confirm: bool, output_path:str) -> str:
    """
    Apply this tool only to nominal data columns to encoding:
        - Use result from univariate_analyst_cat as input to suggest encoding plans

    Args:
        file_path (str): path to the dataset file
        column (str): name of the nominal column to analyze

    Returns:
        - New Encoded columns
    """
    
    if not skip_confirm:
        decision = interrupt({
            "type": "confirm_encoding",
            "column": action.column,
            "action": action.actionType,
            "message": f"Use'{action.actionType}' on '{action.column}'? (approve/reject/edit)",
        })

        if decision.get("decision") == "reject":
            return f"Cancel '{action}' on '{action.column}'"

        if decision.get("decision") == "edit":
            action = decision.get("new_action", action)
        
    lf = pl.scan_file(action.file_path, action.file_format)
        
    if action.actionType == EncodingType.FREQUENCY:
        lf = lf.with_columns((pl.len().over(action.column) / pl.len()).alias(f'{action.column}_encoded'))
        encoded_df = lf.collect()
        
    elif action.actionType == EncodingType.LABEL:
        lf = lf.with_columns(pl.col(action.column).cast(pl.Categorical).to_physical().alias(f'{action.column}_encoded'))
        encoded_df = lf.collect()
        
    elif action.actionType == EncodingType.ORDINAL:
        encoded_df = lf.collect()
        unique_vals = encoded_df.get_column(action.column).drop_nulls().unique().sort()
        mapping = {val: i for i, val in enumerate(unique_vals)}
        encoded_df = encoded_df.with_columns(pl.col(action.column).replace(mapping, default=None).cast(pl.Int32).alias(f'{action.column}_encoded'))
        
    elif action.actionType == EncodingType.ONE_HOT:
        encoded_df = lf.collect()
        encoded_df = encoded_df.to_dummies(columns=[action.column])
        
    encoded_df.write_csv(output_path)
    
    with pl.Config(tbl_rows=5, tbl_cols=6):
        sample_str = str(encoded_df.head(5))
    
    return f"Use '{action}' on '{action.column}', save at {output_path}. Output head: {sample_str}"

@tool
def binning_standardizing_tool(action: EngineeringAction, skip_confirm: bool, output_path:str) -> str:
    """
    Apply this tool only to continuos data columns to encoding:
        - Use result from univariate_analyst_cat as input to suggest encoding plans

    Args:
        file_path (str): path to the dataset file
        column (str): name of the continuos column to analyze

    Returns:
        - A new Binned column
    """
    
    if not skip_confirm:
        decision = interrupt({
            "type": "confirm_binning",
            "column": action.column,
            "action": action.actionType,
            "message": f"Use'{action.actionType}' on '{action.column}'? (approve/reject/edit)",
        })

        if decision.get("decision") == "reject":
            return f"Cancel '{action}' on '{action.column}'"

        if decision.get("decision") == "edit":
            action = decision.get("new_action", action)
        
    lf = pl.scan_csv(action.file_path)
    df = lf.select(pl.col(action.column)).collect()
    
    if action.actionType == BinningType.STANDARD:
        mean = df[action.column].mean()
        std = df[action.column].std()
        if std and std > 0:
            new_df = df.with_columns(
                ((pl.col(action.column) - mean) / std).alias(f"{action.column}_std")
            )
        else:
            raise TypeError(f"{std} is NULL or <0")
    elif action.actionType == BinningType.EQUAL:
        min_val = df.select(pl.col(action.column).min()).item()
        max_val = df.select(pl.col(action.column).max()).item()
        
        step = (max_val - min_val) / action.n_bin
        breaks = [min_val + i * step for i in range(1, action.n_bin)]
        
        new_df = df.with_columns(
            pl.col(action.column).cut(breaks).alias(f"{action.column}_binned")
        )
    elif action.actionType == BinningType.QUANTILE:
        new_df = df.with_columns(
                pl.col(action.column)
                .qcut(df[action.column].n_bin, allow_duplicates=True)
                .alias(f"{action.column}_binned")
            )
        
    with pl.Config(tbl_rows=5, tbl_cols=6):
        sample_str = str(new_df.head(5))
    
    return f"Use '{action}' on '{action.column}', save at {output_path}. Output head: {sample_str}"

def executor_node(state: AgentState) -> dict:
    action = state["pending_action"]
    skip_confirm = True if action.risk_level == "low" else False
    fallback_used = False

    try:
        if isinstance(action, CleaningAction):
            result = apply_cleaning_tool.invoke({"action": action, "skip_confirm": skip_confirm, "output_path": state['output_path']})

        elif isinstance(action, EngineeringAction):
            if isinstance(action.actionType, EncodingType):
                result = encoding_tool.invoke({"action": action, "skip_confirm": skip_confirm, "output_path": state['output_path']})
            elif isinstance(action.actionType, BinningType):
                result = binning_standardizing_tool.invoke({"action": action, "skip_confirm": skip_confirm, "output_path": state['output_path']})
            else:
                raise TypeError(f"Unsupported EngineeringAction.actionType: {type(action.actionType).__name__}")
        
        else:
            raise TypeError(f"Unsupported action type for executor: {type(action).__name__}")

    except Exception as e:
        logger.error(f"[executor] Failed to execute action: {e}")
        result = f"EXECUTION_FAILED: {e}"
        fallback_used = True
    
    return {"fallback_used": fallback_used, "skip_confirm": skip_confirm, "action_res": result, 'current_action': action}
    
def review_execution_node(state: AgentState):
    action = state['pending_action']
    result = state["action_res"]

    decision = interrupt({
        "type": "review_output",
        "action": str(action),
        "result": result,
        "message": "Bạn có hài lòng với kết quả này không? (accept/retry/abort)",
    })
    choice = decision.get("decision", "accept")

    if choice == "retry":
        edited_action = decision.get("new_action") 
        return {
            "review_decision": "retry",
            "pending_action": edited_action or action,
            "retry_count": state.get("retry_count", 0) + 1,
        }

    status = "accepted" if choice == "accept" else "rejected"
    
    record = SystemMessage(
        content=(
            f"{result}"
            f"Status: {status}\n"
            f"Attempt: {state.get('retry_count', 0) + 1}"
        )
    )
    
    return {
        "completed_actions": record,
        "pending_action": None,
        "retry_count": 0,
        "review_decision": status
    }
    
def route_after_review(state:AgentState) -> Literal["executor", "validation", "supervisor"]:
    if state["review_decision"] != "retry":
        return "supervisor"
    if state.get("retry_count", 0) >= 3:
        return "supervisor"         
    if state.get("current_action") != state.get("pending_action"):
        return "validation"         
    return "executor"    

executor_graph = StateGraph(AgentState)
executor_graph.add_node("executor", executor_node)
executor_graph.add_node("review", review_execution_node)

executor_graph.add_edge(START, "executor")
executor_graph.add_edge("executor", "review")
executor_graph.add_conditional_edges(
    "review",
    route_after_review,
    {
        "executor": "executor",
        "validation": "validation",
        "supervisor": "supervisor",
    },
)

executor = executor_graph.compile()