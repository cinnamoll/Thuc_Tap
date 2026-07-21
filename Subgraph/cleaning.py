from dotenv import load_dotenv
import os
from langgraph.graph import StateGraph, START, END
from typing import Annotated, Sequence, List, Optional, TypedDict, Literal
from enum import Enum
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, ToolMessage
from operator import add as add_messages
from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace, HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.tools import tool, StructuredTool
from langgraph.prebuilt import ToolNode, tools_condition
import polars as pl
from langgraph.types import interrupt, Command
from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import BaseModel, Field, field_validator

from BT_Thuc_Tap.Class.AgentState import AgentState
from BT_Thuc_Tap.Class.BaseClass import BaseAction
load_dotenv()

hf_endpoint = HuggingFaceEndpoint(
    repo_id='Qwen/Qwen2.5-7B-Instruct',
)

llm = ChatHuggingFace(llm=hf_endpoint) 

class CleaningActionType(str, Enum):
    DROP_ROWS = "drop_rows"
    IMPUTE_MEDIAN = "impute_median"
    IMPUTE_MEAN = "impute_mean"
    IMPUTE_MODE = "impute_mode"
    CAST_DTYPE = "cast_dtype"
    DROP_COLUMN = "drop_column"

class CleaningAction(BaseAction):
    column: str
    actionType: CleaningActionType
    target_dtype: str

    @field_validator("target_dtype")
    @classmethod
    def require_dtype_for_cast(cls, v, info):
        if info.data.get("actionType") == CleaningActionType.CAST_DTYPE and not v:
            raise ValueError("cast_dtype needs target_dtype")
        return v

@tool
def profile_dataset(file_path: str, file_format:str) -> dict:
    """
    Scan a dataset (lazy, not loading the entire dataset into RAM) and return statistics:
    dtypes, number of nulls for both numerical and categorical columns and unique values for categorical column.
    Used to detect problems before suggesting cleaning.
    """
    lf = pl.scan_file(file_path, file_format)
    schema = lf.collect_schema()
    stats = lf.select([
        pl.all().null_count().name.suffix("_nulls"),
        pl.all().n_unique().name.suffix("_nunique"),
    ]).collect(streaming=True)

    return {
        "columns": list(schema.names()),
        "dtypes": {k: str(v) for k, v in schema.items()},
        "stats": stats.to_dicts()[0],
        "n_rows": lf.select(pl.len()).collect().item()
    }

cleaning_tools = [profile_dataset]
cleaning_llm = llm.bind_tools(cleaning_tools)
cleaning_tools_dict = {cleaning_tool.name: cleaning_tool for cleaning_tool in cleaning_tools}


def data_cleaning_node(state:AgentState):
    messages = state['messages']
    system_prompt = SystemMessage(
        content="""
        You are a data cleaning INVESTIGATION agent. You do NOT execute any cleaning action.
        Required procedure:
        1. Always call profile_dataset first to understand the dataset's problems.
        2. Based on the results, analyze which columns have problems (nulls, wrong dtype, etc).
        3. Once you have enough information, stop calling tools and summarize your findings
        and recommended action in plain text — a separate step will convert this into
        a structured action.
        """
    )
    response = cleaning_llm.invoke([system_prompt] + messages)
    return {'messages': [response]}    

def propose_action_node(state: AgentState) -> AgentState:
    structured_llm = llm.with_structured_output(CleaningAction)
    action = structured_llm.invoke(state["messages"])
    return {"cleaning_action": action}

def route_tool_or_finish(state) -> Literal["cleaning_tools", "propose_action"]: #type:ignore
    last_msg = state["messages"][-1]
    if getattr(last_msg, "tool_calls", None):
        return "cleaning_tools"
    return "propose_action"

def take_action_cleaning(state:AgentState) -> AgentState:
    tool_calls = state['messages'][-1].tool_calls
    results = []
    for t in tool_calls:
        if not t['name'] in cleaning_tools_dict: 
            print(f"\nTool: {t['name']} does not exist.")
            result = "Incorrect Tool Name, Please Retry and Select tool from List of Available tools."
        
        else:
            result = cleaning_tools_dict[t['name']].invoke(t['args'])
            print(f"Result length: {len(str(result))}")
            
        results.append(ToolMessage(tool_call_id=t['id'], name=t['name'], content=str(result)))

    print("Tools Execution Complete. Back to the supervisor!")
    return {'messages': results}

cleaning_graph = StateGraph(AgentState)
cleaning_graph.add_node('cleaning_agent', data_cleaning_node)
cleaning_graph.add_node('cleaning_tools', take_action_cleaning)
cleaning_graph.add_node("propose_action", propose_action_node)

cleaning_graph.add_edge(START, "cleaning_agent")
cleaning_graph.add_conditional_edges(
    "cleaning_agent",
    route_tool_or_finish,
    {"cleaning_tools": "cleaning_tools", "propose_action": "propose_action"},
)
cleaning_graph.add_edge("propose_action", END)
cleaning_graph.add_edge("cleaning_tools", "cleaning_agent")

cleaning = cleaning_graph.compile()