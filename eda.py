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

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    cols: Optional[List[str]]
    metadata: Optional[List[str]]
    file_path: str
    file_format: str
    current_step: str
    next_step: str
    completed_steps: Optional[List[str]]
    
@tool
def univariate_analyst_numeric(file_path: str, column: str) -> str:
    """
    Apply this tool only to numeric data columns to extract statistical analysis containing:
        - Measures central tendency (mean, median) to find the typical value.
        - Measures dispersion (range, variance, standard deviation) to see how data spreads.
        - Detects patterns like skewness or outliers that affect data interpretation.

    Args:
        file_path (str): path to the dataset file
        column (str): name of the numeric column to analyze

    Returns:
        A text summary of the statistical analysis for the given column.
    """
    lf = pl.scan_csv(file_path)
    schema = lf.collect_schema()

    if column not in schema.names():
        return f"'{column}' not found in dataset."

    dtype = schema[column]
    if dtype not in (pl.Int8, pl.Int16, pl.Int32, pl.Int64,
                      pl.Float32, pl.Float64, pl.UInt8, pl.UInt16, pl.UInt32, pl.UInt64):
        return f"'{column}' is not numeric (dtype={dtype}). Use a categorical analysis tool instead."

    stats = lf.select([
        pl.col(column).mean().alias("mean"),
        pl.col(column).median().alias("median"),
        pl.col(column).min().alias("min"),
        pl.col(column).max().alias("max"),
        pl.col(column).var().alias("variance"),
        pl.col(column).std().alias("std"),
        pl.col(column).skew().alias("skewness"),
        pl.col(column).quantile(0.25).alias("q1"),
        pl.col(column).quantile(0.75).alias("q3"),
        pl.col(column).null_count().alias("null_count"),
        pl.col(column).count().alias("count"),
    ]).collect(streaming=True).to_dicts()[0]

    q1, q3 = stats["q1"], stats["q3"]
    iqr = q3 - q1
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr

    outlier_count = lf.select(
        pl.col(column).filter(
            (pl.col(column) < lower_bound) | (pl.col(column) > upper_bound)
        ).count().alias("outliers")
    ).collect(streaming=True).item()

    skew = stats["skewness"]
    if skew is None:
        skew_desc = "không xác định"
    elif abs(skew) < 0.5:
        skew_desc = "approximately symmetric"
    elif skew > 0.5:
        skew_desc = "right-skewed"
    else:
        skew_desc = "left-skewed / negative skew"

    range_val = stats["max"] - stats["min"]
    
    res = f"""
        Univariate analysis on {column}
        Valid value: {stats['count']} (null: {stats['null_count']})
        Central tendency: 
            - Mean:   {stats['mean']:.4f}
            - Median: {stats['median']:.4f}
        
        Dispersion:
            - Range:    {range_val:.4f} (min={stats['min']:.4f}, max={stats['max']:.4f})
            - Variance: {stats['variance']:.4f}
            - Std Dev:  {stats['std']:.4f}
            - IQR:      {iqr:.4f} (Q1={q1:.4f}, Q3={q3:.4f})
        
        Distribution shape:
            - Skewness: {skew:.4f} → {skew_desc}
            - Outliers (IQR method, outside [{lower_bound:.4f}, {upper_bound:.4f}]): {outlier_count} values
    
    """
    return res.strip()
    
    
@tool
def univariate_analyst_cat(file_path: str, column: str) -> str:
    """
    Apply this tool only to nominal data columns to extract statistical analysis containing:
        - Unique column values, mode and count of distinct categories in our variable
        - Generate a frequency table, containing 6 columns [Column_value, Value_count, Frequency, Percentage]
        divided into 2 parts of Valid values and Missing Values

    Args:
        file_path (str): path to the dataset file
        column (str): name of the nominal column to analyze

    Returns:
        A text summary of the statistical analysis for the given column.
    """
    lf = pl.scan_csv(file_path)
    schema = lf.collect_schema()

    if column not in schema.names():
        return f"'{column}' not found in dataset."

    dtype = schema[column]
    if dtype not in (pl.Categorical, pl.String) and not isinstance(dtype, pl.Enum):
        return f"'{column}' is not a nominal/categorical type (dtype={dtype}). Use a numeric analysis tool instead."
    
    stats = lf.select([
        pl.col(column).drop_nulls().mode().implode().alias("mode"),
        pl.col(column).drop_nulls().n_unique().alias("n_unique"),
        pl.col(column).is_not_null().sum().alias("valid_count"),
        pl.col(column).is_null().sum().alias("null_count"),
        pl.len().alias("total_count")
    ]).collect()

    modes = stats.get_column("mode").item()
    n_unique = stats.get_column("n_unique").item()
    valid_count = stats.get_column("valid_count").item()
    null_count = stats.get_column("null_count").item()
    total_count = stats.get_column("total_count").item()

    df = lf.select(pl.col(column)).collect()

    freq_table = (
        df.group_by(column)
        .agg(pl.len().alias("Value_count"))
        .with_columns(
            (pl.col("Value_count") / total_count).alias("Frequency"),
            ((pl.col("Value_count") / total_count) * 100).alias("Percentage")
        )
        .sort("Value_count", descending=True)
        .rename({column: "Column_value"})
    )

    valid_df = freq_table.filter(pl.col("Column_value").is_not_null())
    missing_df = freq_table.filter(pl.col("Column_value").is_null())

    with pl.Config(tbl_rows=valid_df.height if valid_df.height > 0 else 1, tbl_cols=4):
        valid_str = str(valid_df) if not valid_df.is_empty() else "No valid data found."
        
    with pl.Config(tbl_rows=missing_df.height if missing_df.height > 0 else 1, tbl_cols=4):
        missing_str = str(missing_df) if not missing_df.is_empty() else "No missing values."

    mode_str = ', '.join(map(str, modes)) if modes else "None"

    res = f"""
        Univariate analysis on {column}
        Valid value: {valid_count} (null: {null_count})
        Central tendency: 
            - Mode:                {mode_str}
            - Distinct Categories: {n_unique}
        
        Distribution (Valid Values):
        {valid_str}
        
        Missing Values Analysis:
        {missing_str}
    """
    
    return res
    
# @tool 
# def multivariate_analyst(file_path: str, column: str) -> str:
#     pass

# @tool
# def draw_graph(
#     column: str,
#     metadata: str
# ):
#     pass
    
eda_tools = [univariate_analyst_numeric, univariate_analyst_cat]
eda_llm = llm.bind_tools(tools=eda_tools)
eda_tools_dict = {eda_tool.name: eda_tool for eda_tool in eda_tools}

def take_action_eda(state:AgentState) -> AgentState:
    tool_calls = state['messages'][-1].tool_calls
    results = []
    for t in tool_calls:
        print(f"Calling Tool: {t['name']} with query: {t['args'].get('query', 'No query provided')}")
        
        if not t['name'] in eda_tools_dict: 
            print(f"\nTool: {t['name']} does not exist.")
            result = "Incorrect Tool Name, Please Retry and Select tool from List of Available tools."
        
        else:
            result = eda_tools_dict[t['name']].invoke(t['args'].get('query', ''))
            print(f"Result length: {len(str(result))}")
            
        results.append(ToolMessage(tool_call_id=t['id'], name=t['name'], content=str(result)))

    print("Tools Execution Complete. Back to the supervisor!")
    return {'messages': results}

def route_tool_or_finish(state) -> Literal["eda_tools", END]: #type:ignore
    last_msg = state["messages"][-1]
    if getattr(last_msg, "tool_calls", None):
        return "eda_tools"
    return END

def eda_agent_node(state: AgentState):
    response = eda_llm.invoke(state["messages"])
    return {"messages": [response]}

eda_graph = StateGraph(AgentState)
eda_graph.add_node('eda_agent', eda_agent_node)
eda_graph.add_node('eda_tools', take_action_eda)

eda_graph.add_edge(START, "eda_agent")
eda_graph.add_conditional_edges(
    "eda_agent",
    route_tool_or_finish,
    {"eda_tools": "eda_tools", END: END},
)
eda_graph.add_edge("eda_tools", "eda_agent")

eda = eda_graph.compile()