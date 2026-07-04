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
from pydantic import BaseModel, FilePath
import polars as pl
from langgraph.types import interrupt, Command
from dotenv import load_dotenv

load_dotenv()

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    cols: Optional[List[str]]
    metadata: Optional[List[str]]
    file_path: str
    file_format: str
    

@tool
def extract_columns(state:AgentState) -> str:
    """
    This tool reads and extracts column name from the file
    Args:
        file_path (str): metadata file path 
    
    Return:
        List of column names
    """
    if not os.path.exists(state['file_path']):
        return []    
    cols = []
    
    try:
        if state['file_format'] == 'csv':
            df = pl.read_csv(state['file_path'])
            cols = df.columns
        elif state['file_format'] in ['xlsx', 'xls']:
            df = pl.read_excel(state['file_path'])
            cols = df.columns
        elif state['file_format'] == 'json':
            df = pl.read_json(state['file_path'])
            cols = df.columns
    except Exception as e:
        return str(e)

    return cols

class CleaningAction(BaseModel):
    column: str
    issue: str                 
    proposed_action: str      
    status: Literal["pending", "approved", "rejected", "edited"] = "pending"
    
@tool
def profile_dataset(file_path: str) -> dict:
    """
    Scan a dataset (lazy, not loading the entire dataset into RAM) and return statistics:
    dtypes, number of nulls and unique values ​​per column.
    Used to detect problems before suggesting cleaning.
    """
    lf = pl.scan_csv(file_path)
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
    target_dtype: str = "",
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
    return f"Use '{action}' on '{column}', save value at {output_path}"
    
tools = [extract_columns, profile_dataset, apply_cleaning]

hf_endpoint = HuggingFaceEndpoint(
    repo_id='Qwen/Qwen2.5-7B-Instruct',
)

llm = ChatHuggingFace(llm=hf_endpoint).bind_tools(tools=tools)    

def extract_metadata_node(state: AgentState):
    """
    This node invokes the LLM. If the user asks about a dataset, 
    the LLM will generate a tool_call to 'extract_columns'.
    """
    messages = state['messages']
    
    system_prompt = SystemMessage(
        content="""
            You are a data assistant. NEVER call extract_columns with a placeholder 
            or example file path. If the user has not provided a real, specific file 
            path, ask them for it instead of guessing. 
            
            After receiving tool results, generate plain-language business descriptions 
            for each column (e.g., "The age of the passenger in years" or "The ticket class").
            NEVER invent columns that were not returned by the tool.
            
            Update 'file_path', 'file_format' in state by the path in HumanMessage
            
            Return the response EXACTLY in the format of 2 Python lists:
            column_name = [...]
            column_metadata = [...] # Put your plain-language descriptions here
            
            Do not include any extra text, notes, or markdown formatting outside the lists.
        """
    )
    
    response = llm.invoke([system_prompt] + messages)
    # print(state)
    return {'messages': [response]}

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

graph = StateGraph(AgentState)
graph.add_node('extract_metadata', extract_metadata_node)
graph.add_node('clean_dataset', data_cleaning_node)
graph.add_node('tools', ToolNode(tools=tools))

graph.add_edge(START, 'extract_metadata')
graph.add_conditional_edges(
    'extract_metadata',
    tools_condition
)
graph.add_edge('tools', 'extract_metadata')
graph.add_edge('extract_metadata', 'clean_dataset')

app = graph.compile()

user_input = input("Enter: ")
while user_input.lower() != 'exit':
    for event in app.stream({'messages': [HumanMessage(content=user_input)]}):
        for node_name, node_state in event.items():
            print(f"\n--- Output from {node_name} ---")
            last_message = node_state['messages'][-1]
            print(last_message.content if last_message.content else "[Tool Call]")
            
    user_input = input("Enter: ")