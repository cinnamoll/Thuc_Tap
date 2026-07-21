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