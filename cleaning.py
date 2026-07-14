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

from AgentState import AgentState

load_dotenv()

hf_endpoint = HuggingFaceEndpoint(
    repo_id='Qwen/Qwen2.5-7B-Instruct',
)

llm = ChatHuggingFace(llm=hf_endpoint) 

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
    }

@tool
def apply_cleaning(
    file_path: str,
    column: str,
    action: Literal["drop_rows", "impute_median", "impute_mean", "impute_mode", "cast_dtype", "drop_column"],
    output_path: str,
    target_dtype: str = ""
) -> str:
    """
    Apply a specific cleaning action to a column of the dataset and write the results to a new file.
    Only call this tool after clearly identifying the problem via profile_dataset.
    This tool will pause and wait for user confirmation before actually overwriting the data.
    """
    
    decision = interrupt({
        "type": "confirm_cleaning",
        "column": column,
        "action": action,
        "message": f"Use'{action}' on '{column}'? (approve/reject/edit)",
    })

    if decision.get("decision") == "reject":
        return f"Cancel '{action}' on '{column}'"

    if decision.get("decision") == "edit":
        action = decision.get("new_action", action)

    lf = pl.scan_csv(file_path)

    if action == "drop_rows":
        lf = lf.drop_nulls(subset=[column])
    elif action == "impute_median":
        lf = lf.with_columns(pl.col(column).fill_null(pl.col(column).median()))
    elif action == "impute_mean":
        lf = lf.with_columns(pl.col(column).fill_null(pl.col(column).mean()))
    elif action == "impute_mode":
        lf = lf.with_columns(pl.col(column).fill_null(pl.col(column).mode().first()))
    elif action == "cast_dtype":
        lf = lf.with_columns(pl.col(column).cast(getattr(pl, target_dtype)))
    elif action == "drop_column":
        lf = lf.drop(column)

    lf.sink_csv(output_path) 
    return f"Use '{action}' on '{column}', save at {output_path}"

cleaning_tools = [profile_dataset, apply_cleaning]
cleaning_llm = llm.bind_tools(cleaning_tools)
cleaning_tools_dict = {cleaning_tool.name: cleaning_tool for cleaning_tool in cleaning_tools}

def data_cleaning_node(state:AgentState):
    messages = state['messages']
    system_prompt = SystemMessage(
        content="""
        You are a data cleaning agent. Required procedure:
        1.Always call profile_dataset first to understand the dataset's problems.
        2.Based on the results, suggest appropriate cleaning actions for each problematic column,
        briefly explain the reason before calling apply_cleaning.
        3.Call apply_cleaning for each column individually, do not group multiple columns in one call.
        4.After completing all problematic columns, summarize the changes made.
        """
    )
    response = llm.invoke([system_prompt] + messages)
    return {'messages': [response]}    

def route_tool_or_finish(state) -> Literal["cleaning_tools", END]: #type:ignore
    last_msg = state["messages"][-1]
    if getattr(last_msg, "tool_calls", None):
        return "cleaning_tools"
    return END

def take_action_cleaning(state:AgentState) -> AgentState:
    tool_calls = state['messages'][-1].tool_calls
    results = []
    for t in tool_calls:
        print(f"Calling Tool: {t['name']} with query: {t['args'].get('query', 'No query provided')}")
        
        if not t['name'] in cleaning_tools_dict: 
            print(f"\nTool: {t['name']} does not exist.")
            result = "Incorrect Tool Name, Please Retry and Select tool from List of Available tools."
        
        else:
            result = cleaning_tools_dict[t['name']].invoke(t['args'].get('query', ''))
            print(f"Result length: {len(str(result))}")
            
        results.append(ToolMessage(tool_call_id=t['id'], name=t['name'], content=str(result)))

    print("Tools Execution Complete. Back to the supervisor!")
    return {'messages': results}

cleaning_graph = StateGraph(AgentState)
cleaning_graph.add_node('cleaning_agent', data_cleaning_node)
cleaning_graph.add_node('cleaning_tools', take_action_cleaning)

cleaning_graph.add_edge(START, "cleaning_agent")
cleaning_graph.add_conditional_edges(
    "cleaning_agent",
    route_tool_or_finish,
    {"cleaning_tools": "cleaning_tools", END: END},
)
cleaning_graph.add_edge("cleaning_tools", "cleaning_agent")

cleaning = cleaning_graph.compile()