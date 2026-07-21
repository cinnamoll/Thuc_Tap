from dotenv import load_dotenv
import os
from langgraph.graph import StateGraph, START, END
from typing import Annotated, Sequence, List, Optional, TypedDict, Literal
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, ToolMessage
from operator import add as add_messages
from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace
from langchain_chroma import Chroma
from langchain_core.tools import tool, StructuredTool
from langgraph.prebuilt import ToolNode, tools_condition
import polars as pl
from langgraph.types import interrupt, Command
from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import BaseModel, Field, field_validator
from enum import Enum

from BT_Thuc_Tap.Class.AgentState import AgentState
from BT_Thuc_Tap.Class.BaseClass import BaseAction

load_dotenv()

hf_endpoint = HuggingFaceEndpoint(
    repo_id='Qwen/Qwen2.5-7B-Instruct',
)

llm = ChatHuggingFace(llm=hf_endpoint) 

class EngineeringType(str, Enum):
    LABEL = "label_encoding" 
    ORDINAL = "ordinal_encoding"
    FREQUENCY = "frequency_encoding"
    ONE_HOT = "one_hot_encoding"
    EQUAL_WIDTH = "equal_width"
    QUANTILE = "quantile"
    STANDARDIZE = "standardize"

class EngineeringAction(BaseAction):
    column: str
    actionType: EngineeringType
    target_dtype: str

    @field_validator("target_dtype")
    @classmethod
    def require_dtype_for_cast(cls, v, info):
        if info.data.get("actionType") == EngineeringType.CAST_DTYPE and not v:
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

@tool
def encoding_tool(
    file_path: str, 
    column: str,
    action: Literal["label_encoding", "ordinal_encoding", "frequency_encoding", "one_hot_encoding"]
) -> str:
    """
    Apply this tool only to nominal data columns to encoding:
        - Use result from univariate_analyst_cat as input to suggest encoding plans

    Args:
        file_path (str): path to the dataset file
        column (str): name of the nominal column to analyze

    Returns:
        - New Encoded column
    """
    lf = pl.scan_csv(file_path)
    schema = lf.collect_schema()

    if column not in schema.names():
        return f"'{column}' not found in dataset."

    dtype = schema[column]
    if dtype not in (pl.Categorical, pl.String) and not isinstance(dtype, pl.Enum):
        return f"'{column}' is not a nominal/categorical type (dtype={dtype})"
    
    decision = interrupt({
        "type": "confirm_encoding",
        "column": column,
        "action": action,
        "message": f"Use'{action}' on '{column}'? (approve/reject/edit)",
    })
    
    if decision.get("decision") == "reject":
        return f"Cancel '{action}' on '{column}'"

    if decision.get("decision") == "edit":
        action = decision.get("new_action", action)
        
    df = lf.select(pl.col(column)).collect()
    
    if action == 'frequency_encoding':
        encoded_df = df.with_columns(
            (pl.len().over(column) / df.height).alias(f'{column}_encoded')
        )   
    elif action == 'label_encoding':
        encoded_df = df.with_columns(
            pl.col(column).cast(pl.Categorical).to_physical().alias(f'{column}_encoded')
        )
    elif action == 'ordinal_encoding':
        unique_vals = df.get_column(column).drop_nulls().unique().sort()
        mapping = {val: i for i, val in enumerate(unique_vals)}
            
        encoded_df = df.with_columns(
            pl.col(column).replace(mapping, default=None).cast(pl.Int32).alias(f'{column}_encoded')
        )   
    elif action == 'one_hot_encoding':
        encoded_df = df.to_dummies(columns=[column])
        
    with pl.Config(tbl_rows=5, tbl_cols=6):
        sample_str = str(encoded_df.head(5))
    
    res = f"""
        Encoding Action Completed:
        - Target Column: '{column}'
        - Method Applied: {action}
        - New DataFrame Glimpse (First 5 rows):
        {sample_str}
    """
    
    return res

@tool
def binning_standardizing_tool(
    file_path: str, 
    column: str,
    action: Literal["equal_width", "quantile", "standardize"],
    n_bin: Optional[int]
) -> str:
    """
    Apply this tool only to continuos data columns to encoding:
        - Use result from univariate_analyst_cat as input to suggest encoding plans

    Args:
        file_path (str): path to the dataset file
        column (str): name of the continuos column to analyze

    Returns:
        - A new Binned column
    """
    lf = pl.scan_csv(file_path)
    schema = lf.collect_schema()

    if column not in schema.names():
        return f"'{column}' not found in dataset."

    dtype = schema[column]
    if dtype not in (pl.Int8, pl.Int16, pl.Int32, pl.Int64,
                      pl.Float32, pl.Float64, pl.UInt8, pl.UInt16, pl.UInt32, pl.UInt64):
        return f"'{column}' is not numeric (dtype={dtype})"
    
    decision = interrupt({
        "type": "confirm_encoding",
        "column": column,
        "action": action,
        "message": f"Use'{action}' on '{column}'? (approve/reject/edit)",
    })
    
    if decision.get("decision") == "reject":
        return f"Cancel '{action}' on '{column}'"

    if decision.get("decision") == "edit":
        action = decision.get("new_action", action)
        
    df = lf.select(pl.col(column)).collect()
    
    if action == 'standardize':
        mean = df[column].mean()
        std = df[column].std()
        if std and std > 0:
            new_df = df.with_columns(
                ((pl.col(column) - mean) / std).alias(f"{column}_std")
            )
    elif action == 'equal_width':
        min_val = df.select(pl.col(column).min()).item()
        max_val = df.select(pl.col(column).max()).item()
        
        step = (max_val - min_val) / n_bin
        breaks = [min_val + i * step for i in range(1, n_bin)]
        
        new_df = df.with_columns(
            pl.col(column).cut(breaks).alias(f"{column}_binned")
        )
    elif action == 'quantile':
        new_df = df.with_columns(
                pl.col(column)
                .qcut(df[column].bin_count, allow_duplicates=True)
                .alias(f"{column}_binned")
            )
        
    with pl.Config(tbl_rows=5, tbl_cols=6):
        sample_str = str(new_df.head(5))
    
    res = f"""
        Binning Action Completed:
        - Target Column: '{column}'
        - Method Applied: {action}
        - New DataFrame Glimpse (First 5 rows):
        {sample_str}
    """
    
    return res
    
# @tool
# def preview_feature():
#     pass

feature_tools = [profile_dataset, encoding_tool, binning_standardizing_tool]
feature_llm = llm.bind_tools(tools=feature_tools)
feature_tools_dict = {feature_tool.name: feature_tool for feature_tool in feature_tools}

def feature_agent_node(state: AgentState):
    response = feature_llm.invoke(state["messages"])
    return {"messages": [response]}

def propose_action_node(state: AgentState) -> AgentState:
    structured_llm = llm.with_structured_output(EngineeringAction)
    action = structured_llm.invoke(state["messages"])
    return {"cleaning_action": action}

def take_action_feature(state:AgentState) -> AgentState:
    tool_calls = state['messages'][-1].tool_calls
    results = []
    for t in tool_calls:
        print(f"Calling Tool: {t['name']} with query: {t['args'].get('query', 'No query provided')}")
        
        if not t['name'] in feature_tools_dict: 
            print(f"\nTool: {t['name']} does not exist.")
            result = "Incorrect Tool Name, Please Retry and Select tool from List of Available tools."
        
        else:
            result = feature_tools_dict[t['name']].invoke(t['args'])
            print(f"Result length: {len(str(result))}")
            
        results.append(ToolMessage(tool_call_id=t['id'], name=t['name'], content=str(result)))

    print("Tools Execution Complete. Back to the supervisor!")
    return {'messages': results}

def route_tool_or_finish(state) -> Literal["feature_tools", "propose_action"]: #type:ignore
    last_msg = state["messages"][-1]
    if getattr(last_msg, "tool_calls", None):
        return "feature_tools"
    return "propose_action"

feature_graph = StateGraph(AgentState)
feature_graph.add_node('feature_agent', feature_agent_node)
feature_graph.add_node('feature_tools', take_action_feature)
feature_graph.add_node('propose_action', propose_action_node)

feature_graph.add_edge(START, 'feature_agent')
feature_graph.add_conditional_edges(
    "feature_agent",
    route_tool_or_finish,
    {"feature_tools": "feature_tools", 'propose_action': 'propose_action'},
)
feature_graph.add_edge('propose_action', END)
feature_graph.add_edge("feature_tools", "feature_agent")

feature_engineering = feature_graph.compile()