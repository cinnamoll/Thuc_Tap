from langchain_core.messages import SystemMessage
from langchain_core.tools import tool
import pandas as pd
import numpy as np
from langgraph.types import interrupt

from Class.AgentState import AgentState
from Class.CleaningAction import CleaningAction, CleaningActionType
from Class.EDAInsight import EDAInsight
from Class.EngineeringAction import EngineeringAction, EncodingType, BinningType

def read_df(file_path: str, file_format: str) -> pd.DataFrame:
    if file_format == "csv":
        df = pd.read_csv(file_path)
    elif file_format == "parquet":
        df = pd.read_parquet(file_path)
    elif file_format == "json":
        df = pd.read_json(file_path, lines=True)
    else:
        raise ValueError(f"Don't support {file_format}")
    return df

DTYPE_MAP = {
    "int8": np.int8, "int16": np.int16, "int32": np.int32, "int64": np.int64,
    "uint8": np.uint8, "uint16": np.uint16, "uint32": np.uint32, "uint64": np.uint64,
    "float32": np.float32, "float64": np.float64, "float": np.float64, "double": np.float64,
    "str": "string", "string": "string", "utf8": "string",
    "bool": "boolean", "boolean": "boolean",
    "date": "datetime64[ns]", "datetime": "datetime64[ns]", "time": "datetime64[ns]",
    "categorical": "category",
}

@tool
def cleaning_tool(action: CleaningAction, output_path: str) -> str:
    """
    Apply a specific cleaning action to a column of the dataset and write the results to a new file.
    Only call this tool after clearly identifying the problem via profile_dataset.
    This tool will pause and wait for user confirmation before actually overwriting the data.
    """
    df = read_df(action.file_path, action.file_format)
    if action.column not in df.columns:
        raise ValueError(f"Column '{action.column}' not found in dataset. Valid columns: {df.columns.tolist()}")

    if action.actionType == CleaningActionType.DROP_ROWS:
        df = df.dropna(subset=[action.column])
    elif action.actionType == CleaningActionType.IMPUTE_MEDIAN:
        df[action.column] = df[action.column].fillna(df[action.column].median())
    elif action.actionType == CleaningActionType.IMPUTE_MEAN:
        df[action.column] = df[action.column].fillna(df[action.column].mean())
    elif action.actionType == CleaningActionType.IMPUTE_MODE:
        mode_val = df[action.column].mode()
        if not mode_val.empty:
            df[action.column] = df[action.column].fillna(mode_val.iloc[0])
    elif action.actionType == CleaningActionType.CAST_DTYPE:
        target_dtype = DTYPE_MAP.get(str(action.target_dtype).lower())
        if target_dtype is None:
            raise ValueError(
                f"Unsupported target_dtype '{action.target_dtype}'. "
                f"Supported dtypes: {sorted(DTYPE_MAP.keys())}"
            )
        df[action.column] = df[action.column].astype(target_dtype)
    elif action.actionType == CleaningActionType.DROP_COLUMN:
        df = df.drop(columns=[action.column])

    df.to_csv(output_path, index=False) 
    return f"Use '{action}' on '{action.column}', save at {output_path}"

@tool
def encoding_tool(action: EngineeringAction, output_path:str) -> str:
    """
    Apply this tool only to nominal data columns to encoding:
        - Use result from univariate_analyst_cat as input to suggest encoding plans

    Args:
        file_path (str): path to the dataset file
        column (str): name of the nominal column to analyze

    Returns:
        - New Encoded columns
    """        
    df = read_df(action.file_path, action.file_format)
    if action.column not in df.columns:
        raise ValueError(f"Column '{action.column}' not found in dataset. Valid columns: {df.columns.tolist()}")
        
    if action.actionType == EncodingType.FREQUENCY:
        freq_map = df[action.column].value_counts(normalize=True)
        df[f'{action.column}_encoded'] = df[action.column].map(freq_map)
        
    elif action.actionType == EncodingType.LABEL:
        codes, _ = pd.factorize(df[action.column])
        df[f'{action.column}_encoded'] = codes
        
    elif action.actionType == EncodingType.ORDINAL:
        unique_vals = sorted(df[action.column].dropna().unique())
        mapping = {val: i for i, val in enumerate(unique_vals)}
        df[f'{action.column}_encoded'] = df[action.column].map(mapping).astype('Int32')
        
    elif action.actionType == EncodingType.ONE_HOT:
        df = pd.get_dummies(df, columns=[action.column])
        
    df.to_csv(output_path, index=False)
    
    sample_str = df.head(5).to_string(index=False)
    
    return f"Use '{action}' on '{action.column}', save at {output_path}. Output head: {sample_str}"

@tool
def binning_standardizing_tool(action: EngineeringAction, output_path:str) -> str:
    """
    Apply this tool only to continuos data columns to encoding:
        - Use result from univariate_analyst_cat as input to suggest encoding plans

    Args:
        file_path (str): path to the dataset file
        column (str): name of the continuos column to analyze

    Returns:
        - A new Binned column
    """
    df = read_df(action.file_path, action.file_format)
    if action.column not in df.columns:
        raise ValueError(f"Column '{action.column}' not found in dataset. Valid columns: {df.columns.tolist()}")

    series = df[action.column]
    
    if action.actionType == BinningType.STANDARD:
        mean = series.mean()
        std = series.std()
        if std and std > 0:
            new_df = df[[action.column]].copy()
            new_df[f"{action.column}_std"] = (series - mean) / std
        else:
            raise TypeError(f"{std} is NULL or <0")
    elif action.actionType == BinningType.EQUAL:
        min_val = series.min()
        max_val = series.max()
        
        step = (max_val - min_val) / action.n_bin
        breaks = [min_val + i * step for i in range(1, action.n_bin)]
        
        new_df = df[[action.column]].copy()
        new_df[f"{action.column}_binned"] = pd.cut(series, bins=[min_val] + breaks + [max_val], include_lowest=True)
    elif action.actionType == BinningType.QUANTILE:
        new_df = df[[action.column]].copy()
        new_df[f"{action.column}_binned"] = pd.qcut(series, q=action.n_bin, duplicates='drop')
        
    new_df.to_csv(output_path, index=False)    
    
    sample_str = new_df.head(5).to_string(index=False)
    
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
    run_id = state.get('run_id')
    output_path = state.get('output_path') or f"output_{action_type}_{run_id}_{action.column}.csv"

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
            return {"action_res": f"Cancel '{action}' on '{action.column}'", "skip_confirm": skip_confirm, "fallback_used": False, "action_status":False}

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
            result = cleaning_tool.invoke({"action": action, "output_path": output_path})
        elif isinstance(action, EngineeringAction):
            if isinstance(action.actionType, EncodingType):
                result = encoding_tool.invoke({"action": action, "output_path": output_path})
            elif isinstance(action.actionType, BinningType):
                result = binning_standardizing_tool.invoke({"action": action, "output_path": output_path})
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
    
    return {"fallback_used": fallback_used, "skip_confirm": skip_confirm, "action_res": result, "current_action": action}
    
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

    status = "accepted" if choice == "accept" else "rejected"
    
    record = SystemMessage(
        content=(
            f"{result}"
            f"Status: {status}\n"
            f"Attempt: {state.get('retry_count', 0) + 1}"
        )
    )
    
    return {"completed_actions": [record], "retry_count": 0, "review_decision": status}