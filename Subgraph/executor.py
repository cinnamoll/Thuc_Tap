from langchain_core.messages import SystemMessage
from langchain_core.tools import tool
import polars as pl
from langgraph.types import interrupt

from Class.AgentState import AgentState
from Class.CleaningAction import CleaningAction, CleaningActionType
from Class.EDAInsight import EDAInsight
from Class.EngineeringAction import EngineeringAction, EncodingType, BinningType

def get_lf(file_path: str, file_format: str):
    if file_format == "csv":
        lf = pl.scan_csv(file_path)
    elif file_format == "parquet":
        lf = pl.scan_parquet(file_path)
    elif file_format == "json":
        lf = pl.scan_ndjson(file_path)
    else:
        raise ValueError(f"Don't support {file_format}")
    return lf

@tool
def apply_cleaning_tool(action: CleaningAction, skip_confirm: bool, output_path: str) -> str:
    """
    Apply a specific cleaning action to a column of the dataset and write the results to a new file.
    Only call this tool after clearly identifying the problem via profile_dataset.
    This tool will pause and wait for user confirmation before actually overwriting the data.
    """
    lf = get_lf(action.file_path, action.file_format)
    schema = lf.collect_schema()
    if action.column not in schema.names():
        raise ValueError(f"Column '{action.column}' not found in dataset. Valid columns: {list(schema.names())}")

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
    lf = get_lf(action.file_path, action.file_format)
    schema = lf.collect_schema()
    if action.column not in schema.names():
        raise ValueError(f"Column '{action.column}' not found in dataset. Valid columns: {list(schema.names())}")
        
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
    lf = get_lf(action.file_path, action.file_format)
    schema = lf.collect_schema()
    if action.column not in schema.names():
        raise ValueError(f"Column '{action.column}' not found in dataset. Valid columns: {list(schema.names())}")

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
                .qcut(action.n_bin, allow_duplicates=True) 
                .alias(f"{action.column}_binned")
            )
        
    new_df.write_csv(output_path)    
    
    with pl.Config(tbl_rows=5, tbl_cols=6):
        sample_str = str(new_df.head(5))
    
    return f"Use '{action}' on '{action.column}', save at {output_path}. Output head: {sample_str}"

def executor_node(state: AgentState) -> dict:
    action_type = state.get('action_type')
    if action_type == 'cleaning':
        action = state['pending_cleaning'][-1]
    elif action_type == 'engineering':
        action = state['pending_engineering'][-1]
    elif action_type == 'insight': 
        action = state['pending_insight'][-1] 
    else:
        raise ValueError(f"Unsupported action_type: {action_type}")
        
    act_type = getattr(action, "actionType", "eda_insight")
    action_id = f"{action.column}_{act_type}"
    reviewed = state.get("reviewed_actions") or []
    output_path = state.get('output_path') or f"output_{action_type}.csv"

    skip_confirm = True if (getattr(action, "risk_level", "low") == "low" or action_id in reviewed) else False 
    fallback_used = False

    if not skip_confirm:
        action_payload = action.model_dump(mode="json") if hasattr(action, "model_dump") else str(action)
        act_type_val = getattr(action.actionType, "value", str(action.actionType)) if hasattr(action, "actionType") else "eda_insight"

        decision = interrupt({
            "type": "confirm_action",
            "column": action.column,
            "actionType": act_type_val,
            "action": action_payload,
            "message": f"Use '{act_type_val}' on '{action.column}'? (approve/reject/edit)",
        })

        dec_str = "approve"
        new_act_data = None

        if isinstance(decision, str):
            dec_str = decision.strip().lower()
        elif isinstance(decision, bool):
            dec_str = "approve" if decision else "reject"
        elif isinstance(decision, dict):
            val = decision.get("decision")
            if val is None:
                val = decision.get("approved")
            if val is None:
                val = decision.get("choice")
            if isinstance(val, bool):
                dec_str = "approve" if val else "reject"
            elif isinstance(val, str):
                dec_str = val.strip().lower()
            new_act_data = decision.get("new_action")

        if dec_str in ["reject", "rejected", "no", "n", "false"]:
            return {"action_res": f"Cancel '{action}' on '{action.column}'", "skip_confirm": skip_confirm, "fallback_used": False}

        if dec_str in ["edit", "retry"]:
            if isinstance(new_act_data, dict):
                if action_type == 'cleaning':
                    action = CleaningAction.model_validate(new_act_data)
                elif action_type == 'engineering':
                    action = EngineeringAction.model_validate(new_act_data)
                elif action_type == 'insight':
                    action = EDAInsight.model_validate(new_act_data)
            elif new_act_data:
                action = new_act_data

    try:
        if isinstance(action, CleaningAction):
            result = apply_cleaning_tool.invoke({"action": action, "skip_confirm": skip_confirm, "output_path": output_path})
        elif isinstance(action, EngineeringAction):
            if isinstance(action.actionType, EncodingType):
                result = encoding_tool.invoke({"action": action, "skip_confirm": skip_confirm, "output_path": output_path})
            elif isinstance(action.actionType, BinningType):
                result = binning_standardizing_tool.invoke({"action": action, "skip_confirm": skip_confirm, "output_path": output_path})
            else:
                raise TypeError(f"Unsupported EngineeringAction.actionType: {type(action.actionType).__name__}")
        elif isinstance(action, EDAInsight):  
            result = f"EDA Insight recorded for column '{action.column}' with metrics: {action.metric_value}" 
        else:
            raise TypeError(f"Unsupported action type for executor: {type(action).__name__}")

    except Exception as e:
        print(f"[executor] Failed to execute action: {e} \n")
        result = f"EXECUTION_FAILED: {e}"
        fallback_used = True
    
    return {
        "fallback_used": fallback_used, 
        "skip_confirm": skip_confirm, 
        "action_res": result, 
        'current_action': action
    }
    
def review_execution_node(state: AgentState):
    action_type = state.get('action_type')
    if action_type in ['cleaning', 'engineering', 'insight']:
        action = state[f'pending_{action_type}'][-1]
    else:
        raise ValueError(f"Unsupported action_type: {action_type}")

    result = state["action_res"]

    action_payload = action.model_dump(mode="json") if hasattr(action, "model_dump") else str(action)
    decision = interrupt({
        "type": "review_output",
        "action": action_payload,
        "result": str(result),
        "message": "Bạn có hài lòng với kết quả này không? (approve/retry/abort)",
    })
    dec_str = "approve"
    new_act_data = None

    if isinstance(decision, str):
        dec_str = decision.strip().lower()
    elif isinstance(decision, bool):
        dec_str = "approve" if decision else "abort"
    elif isinstance(decision, dict):
        val = decision.get("decision")
        if val is None:
            val = decision.get("approved")
        if val is None:
            val = decision.get("choice")
        if isinstance(val, bool):
            dec_str = "approve" if val else "abort"
        elif isinstance(val, str):
            dec_str = val.strip().lower()
        new_act_data = decision.get("new_action")

    if dec_str in ["retry", "edit"]:
        choice = "retry"
    elif dec_str in ["abort", "reject", "cancel", "no", "n", "false"]:
        choice = "abort"
    else:
        choice = "accept"

    if choice == "retry":
        edited_action = new_act_data 
        update_dict = {}
        if edited_action:
            if isinstance(edited_action, dict):
                if action_type == 'cleaning':
                    edited_action = CleaningAction.model_validate(edited_action)
                elif action_type == 'engineering':
                    edited_action = EngineeringAction.model_validate(edited_action)
                elif action_type == 'insight':
                    edited_action = EDAInsight.model_validate(edited_action)

            if action_type == 'cleaning':
                new_list = list(state['pending_cleaning'])
                new_list[-1] = edited_action
                update_dict = {"pending_cleaning": new_list}
            elif action_type == 'engineering':
                new_list = list(state['pending_engineering'])
                new_list[-1] = edited_action
                update_dict = {"pending_engineering": new_list}
            elif action_type == 'insight': 
                new_list = list(state['pending_insight']) 
                new_list[-1] = edited_action 
                update_dict = {"pending_insight": new_list} 

        return {
            "review_decision": "retry",
            **update_dict,
            "retry_count": state.get("retry_count", 0) + 1,
        }

    status = "accepted" if choice == "approve" else "rejected"
    
    record = SystemMessage(
        content=(
            f"{result}"
            f"Status: {status}\n"
            f"Attempt: {state.get('retry_count', 0) + 1}"
        )
    )
    
    return {
        "completed_actions": [record],
        "retry_count": 0,
        "review_decision": status
    }