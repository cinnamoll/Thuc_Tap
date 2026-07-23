from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from typing import Annotated, Sequence, List, Optional, TypedDict, Literal
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, ToolMessage
from operator import add as add_messages
from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace
from langchain_core.tools import tool, StructuredTool
import polars as pl
from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import BaseModel, Field, field_validator
from enum import Enum
from langgraph.types import interrupt, Command


from BT_Thuc_Tap.Class.AgentState import AgentState
from BT_Thuc_Tap.Class.BaseClass import BaseAction

load_dotenv()

hf_endpoint = HuggingFaceEndpoint(
    repo_id='Qwen/Qwen2.5-7B-Instruct',
)

llm = ChatHuggingFace(llm=hf_endpoint) 

class EncodingType(str, Enum):
    LABEL = "label_encoding" 
    ORDINAL = "ordinal_encoding"
    FREQUENCY = "frequency_encoding"
    ONE_HOT = "one_hot_encoding"

class BinningType(str, Enum):
    EQUAL = "equal_width" 
    QUANTILE = "quantile"
    STANDARD = "standardize"

class EngineeringAction(BaseAction):
    column: str
    actionType: EncodingType | BinningType
    n_bin: int=10,

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
def preview_encoding_tool(
    file_path: str,  
    file_format: str,
    column: str, 
    encode: EncodingType,
    length: int=20,
) -> str:
    """
    Apply this tool only to categorical data columns to encoding:
    Args:
        file_path (str): path to the dataset file
        column (str): name of the categorical column to analyze
        encode (EngineeringType.BINNING): type of encoding to use
        length (int): length of binning dataframe head

    Returns:
        - new Encoded column head
    """
    
    lf = pl.scan_file(file_path, file_format)
    schema = lf.collect_schema()

    if column not in schema.names():
        return f"'{column}' not found in dataset."

    dtype = schema[column]
    if dtype not in (pl.Categorical, pl.String) and not isinstance(dtype, pl.Enum):
        return f"'{column}' is not a nominal/categorical type (dtype={dtype})"
    
    df = lf.select(pl.col(column)).collect().head(length)
    
    if encode == 'frequency_encoding':
        encoded_df = df.with_columns(
            (pl.len().over(column) / df.height).alias(f'{column}_encoded')
        )   
    elif encode == 'label_encoding':
        encoded_df = df.with_columns(
            pl.col(column).cast(pl.Categorical).to_physical().alias(f'{column}_encoded')
        )
    elif encode == 'ordinal_encoding':
        unique_vals = df.get_column(column).drop_nulls().unique().sort()
        mapping = {val: i for i, val in enumerate(unique_vals)}
            
        encoded_df = df.with_columns(
            pl.col(column).replace(mapping, default=None).cast(pl.Int32).alias(f'{column}_encoded')
        )   
    elif encode == 'one_hot_encoding':
        encoded_df = df.to_dummies(columns=[column])

    
    res = f"""
        Encoding Action Completed:
        - Target Column: '{column}'
        - Method Applied: {encode}
        - New DataFrame Glimpse (First f{length} rows):
        {encoded_df}
    """
    
    return res

@tool
def preview_binning_standard_tool(
    file_path: str,  
    file_format: str,
    column: str, 
    encode: BinningType,
    n_bin: int=10,
    length: int=20,
) -> str:
    """
    Apply this tool only to continuos data columns to binned / standardized:
        - Use result from univariate_analyst_ as input to suggest encoding plans

    Args:
        file_path (str): path to the dataset file
        column (str): name of the continuos column to analyze
        n_bin (str): number of bins
        encode (EngineeringType.BINNING): type of encoding to use
        length (int): length of binning dataframe head

    Returns:
        - A new Binned column head
    """
    
    lf = pl.scan_file(file_path, file_format)
    schema = lf.collect_schema()

    if column not in schema.names():
        return f"'{column}' not found in dataset."

    dtype = schema[column]
    if dtype not in (pl.Int8, pl.Int16, pl.Int32, pl.Int64,
                      pl.Float32, pl.Float64, pl.UInt8, pl.UInt16, pl.UInt32, pl.UInt64):
        return f"'{column}' is not numeric (dtype={dtype})"
    
    df = lf.select(pl.col(column)).collect().head(length)
    
    if encode == 'standardize':
        mean = df[column].mean()
        std = df[column].std()
        if std is not None and std > 0:
            new_df = df.with_columns(
                ((pl.col(column) - mean) / std).alias(f"{column}_std")
            )
        else:
            return "Std is None. No binning with this column"
    elif encode == 'equal_width':
        min_val = df.select(pl.col(column).min()).item()
        max_val = df.select(pl.col(column).max()).item()
        
        step = (max_val - min_val) / n_bin
        breaks = [min_val + i * step for i in range(1, n_bin)]
        
        new_df = df.with_columns(
            pl.col(column).cut(breaks).alias(f"{column}_binned")
        )
    elif encode == 'quantile':
        new_df = df.with_columns(
                pl.col(column)
                .qcut(n_bin, allow_duplicates=True)
                .alias(f"{column}_binned")
            )
    
    res = f"""
        Binning Action Completed:
        - Target Column: '{column}'
        - Method Applied: {encode}
        - New DataFrame Glimpse (First {length} rows):
        {new_df}
    """
    
    return res
    

feature_tools = [profile_dataset, preview_encoding_tool, preview_binning_standard_tool]
feature_llm = llm.bind_tools(tools=feature_tools)
feature_tools_dict = {feature_tool.name: feature_tool for feature_tool in feature_tools}

def feature_agent_node(state: AgentState):
    messages = state['messages']
    system_prompt = SystemMessage(
        content="""
        You are a data feature engineering INVESTIGATION agent. You do NOT execute any cleaning action.
        Required procedure:
        1. Always call profile_dataset first to understand the dataset's problems.
        2. Call encoding tool for categorical column and preview column(s) head after encoded 
        3. Call standardization tool FIRST then binning tool for numerical column and preview column(s) head 
        after standardized / binned 
        4. Once you have enough information, stop calling tools and summarize your findings
        and recommended action in plain text — a separate step will convert this into
        a structured action.
        """
    )
    response = feature_llm.invoke([system_prompt] + messages)
    return {'messages': [response]} 

def propose_action_node(state: AgentState) -> AgentState:
    structured_llm = llm.with_structured_output(EngineeringAction)
    action = structured_llm.invoke(state["messages"])
    return {"feature_action": action}

def take_action_feature(state:AgentState) -> AgentState:
    tool_calls = state['messages'][-1].tool_calls
    results = []
    for t in tool_calls:        
        if not t['name'] in feature_tools_dict: 
            print(f"\nTool: {t['name']} does not exist.")
            result = "Incorrect Tool Name, Please Retry and Select tool from List of Available tools."
        
        else:
            result = feature_tools_dict[t['name']].invoke(t['args'])
            print(f"Result length: {len(str(result))}")
            
        results.append(ToolMessage(tool_call_id=t['id'], name=t['name'], content=str(result)))

    print("Tools Execution Complete. Back to the supervisor!")
    return {'messages': results}

def route_tool_or_finish(state) -> Literal["feature_tools", "propose_action"]: 
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