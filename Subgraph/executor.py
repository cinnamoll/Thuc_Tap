from dotenv import load_dotenv
import os
from langgraph.graph import StateGraph, START, END
from typing import Annotated, Sequence, List, Optional, TypedDict, Literal
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, ToolMessage
from operator import add as add_messages
from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace, HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.tools import tool, StructuredTool
from langgraph.prebuilt import ToolNode, tools_condition
import polars as pl
from langgraph.types import interrupt, Command
from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import BaseModel, Field

from BT_Thuc_Tap.Class.AgentState import AgentState

# skip_confirmation = action.risk_level in ("low",)
# apply_cleaning.invoke({"action": action, "skip_confirmation": skip_confirmation})

# @tool
# def apply_cleaning(
#     action: CleaningAction,
#     skip_confirm: bool,
#     output_path: str
# ) -> str:
#     """
#     Apply a specific cleaning action to a column of the dataset and write the results to a new file.
#     Only call this tool after clearly identifying the problem via profile_dataset.
#     This tool will pause and wait for user confirmation before actually overwriting the data.
#     """
#     if not skip_confirm:
#         decision = interrupt({
#             "type": "confirm_cleaning",
#             "column": action.column,
#             "action": action.actionType,
#             "message": f"Use'{action.actionType}' on '{action.column}'? (approve/reject/edit)",
#         })

#         if decision.get("decision") == "reject":
#             return f"Cancel '{action}' on '{action.column}'"

#     lf = pl.scan_file(action.file_path, action.file_format)

#     if CleaningActionType.DROP_ROWS:
#         lf = lf.drop_nulls(subset=[action.column])
#     elif CleaningActionType.IMPUTE_MEDIAN:
#         lf = lf.with_columns(pl.col(action.column).fill_null(pl.col(action.column).median()))
#     elif CleaningActionType.IMPUTE_MEAN:
#         lf = lf.with_columns(pl.col(action.column).fill_null(pl.col(action.column).mean()))
#     elif CleaningActionType.IMPUTE_MODE:
#         lf = lf.with_columns(pl.col(action.column).fill_null(pl.col(action.column).mode().first()))
#     elif CleaningActionType.CAST_DTYPE:
#         lf = lf.with_columns(pl.col(action.column).cast(getattr(pl, action.target_dtype)))
#     elif CleaningActionType.DROP_COLUMN:
#         lf = lf.drop(action.column)

#     lf.sink_csv(output_path) 
#     return f"Use '{action}' on '{action.column}', save at {output_path}"

# @tool
# def encoding_tool(
#     file_path: str, 
#     column: str,
#     action: Literal["label_encoding", "ordinal_encoding", "frequency_encoding", "one_hot_encoding"]
# ) -> str:
#     """
#     Apply this tool only to nominal data columns to encoding:
#         - Use result from univariate_analyst_cat as input to suggest encoding plans

#     Args:
#         file_path (str): path to the dataset file
#         column (str): name of the nominal column to analyze

#     Returns:
#         - New Encoded column
#     """
#     lf = pl.scan_csv(file_path)
#     schema = lf.collect_schema()

#     if column not in schema.names():
#         return f"'{column}' not found in dataset."

#     dtype = schema[column]
#     if dtype not in (pl.Categorical, pl.String) and not isinstance(dtype, pl.Enum):
#         return f"'{column}' is not a nominal/categorical type (dtype={dtype})"
    
#     decision = interrupt({
#         "type": "confirm_encoding",
#         "column": column,
#         "action": action,
#         "message": f"Use'{action}' on '{column}'? (approve/reject/edit)",
#     })
    
#     if decision.get("decision") == "reject":
#         return f"Cancel '{action}' on '{column}'"

#     if decision.get("decision") == "edit":
#         action = decision.get("new_action", action)
        
#     df = lf.select(pl.col(column)).collect()
    
#     if action == 'frequency_encoding':
#         encoded_df = df.with_columns(
#             (pl.len().over(column) / df.height).alias(f'{column}_encoded')
#         )   
#     elif action == 'label_encoding':
#         encoded_df = df.with_columns(
#             pl.col(column).cast(pl.Categorical).to_physical().alias(f'{column}_encoded')
#         )
#     elif action == 'ordinal_encoding':
#         unique_vals = df.get_column(column).drop_nulls().unique().sort()
#         mapping = {val: i for i, val in enumerate(unique_vals)}
            
#         encoded_df = df.with_columns(
#             pl.col(column).replace(mapping, default=None).cast(pl.Int32).alias(f'{column}_encoded')
#         )   
#     elif action == 'one_hot_encoding':
#         encoded_df = df.to_dummies(columns=[column])
        
#     with pl.Config(tbl_rows=5, tbl_cols=6):
#         sample_str = str(encoded_df.head(5))
    
#     res = f"""
#         Encoding Action Completed:
#         - Target Column: '{column}'
#         - Method Applied: {action}
#         - New DataFrame Glimpse (First 5 rows):
#         {sample_str}
#     """
    
#     return res

# @tool
# def binning_standardizing_tool(
#     file_path: str, 
#     column: str,
#     action: Literal["equal_width", "quantile", "standardize"],
#     n_bin: Optional[int]
# ) -> str:
#     """
#     Apply this tool only to continuos data columns to encoding:
#         - Use result from univariate_analyst_cat as input to suggest encoding plans

#     Args:
#         file_path (str): path to the dataset file
#         column (str): name of the continuos column to analyze

#     Returns:
#         - A new Binned column
#     """
#     lf = pl.scan_csv(file_path)
#     schema = lf.collect_schema()

#     if column not in schema.names():
#         return f"'{column}' not found in dataset."

#     dtype = schema[column]
#     if dtype not in (pl.Int8, pl.Int16, pl.Int32, pl.Int64,
#                       pl.Float32, pl.Float64, pl.UInt8, pl.UInt16, pl.UInt32, pl.UInt64):
#         return f"'{column}' is not numeric (dtype={dtype})"
    
#     decision = interrupt({
#         "type": "confirm_encoding",
#         "column": column,
#         "action": action,
#         "message": f"Use'{action}' on '{column}'? (approve/reject/edit)",
#     })
    
#     if decision.get("decision") == "reject":
#         return f"Cancel '{action}' on '{column}'"

#     if decision.get("decision") == "edit":
#         action = decision.get("new_action", action)
        
#     df = lf.select(pl.col(column)).collect()
    
#     if action == 'standardize':
#         mean = df[column].mean()
#         std = df[column].std()
#         if std and std > 0:
#             new_df = df.with_columns(
#                 ((pl.col(column) - mean) / std).alias(f"{column}_std")
#             )
#     elif action == 'equal_width':
#         min_val = df.select(pl.col(column).min()).item()
#         max_val = df.select(pl.col(column).max()).item()
        
#         step = (max_val - min_val) / n_bin
#         breaks = [min_val + i * step for i in range(1, n_bin)]
        
#         new_df = df.with_columns(
#             pl.col(column).cut(breaks).alias(f"{column}_binned")
#         )
#     elif action == 'quantile':
#         new_df = df.with_columns(
#                 pl.col(column)
#                 .qcut(df[column].bin_count, allow_duplicates=True)
#                 .alias(f"{column}_binned")
#             )
        
#     with pl.Config(tbl_rows=5, tbl_cols=6):
#         sample_str = str(new_df.head(5))
    
#     res = f"""
#         Binning Action Completed:
#         - Target Column: '{column}'
#         - Method Applied: {action}
#         - New DataFrame Glimpse (First 5 rows):
#         {sample_str}
#     """
    
#     return res