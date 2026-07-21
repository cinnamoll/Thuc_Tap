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
from pydantic import BaseModel, Field, ValidationError

from BT_Thuc_Tap.Class.AgentState import AgentState
from cleaning import CleaningAction, CleaningActionType
from eda import EDAInsight

def route_after_propose(state):
    if isinstance(state.get("pending_output"), EDAInsight):
        return "validator" 
    return "compute_impact"  

def compute_impact(action: CleaningAction, profile: dict) -> CleaningAction:
    stats = profile["stats"]
    total_rows = profile.get("n_rows") 

    if action.action == CleaningActionType.DROP_ROWS:
        affected = stats.get(f"{action.column}_nulls", 0)
    elif action.action == CleaningActionType.DROP_COLUMN:
        affected = total_rows 
    else:
        affected = 0  

    action.rows_affected = affected
    action.rows_affected_pct = affected / total_rows if total_rows else 0.0
    return action

def risk_node():
    pass

def validator_node():
    pass



