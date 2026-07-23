from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from typing import List, Optional, Literal
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, ToolMessage
from operator import add as add_messages
from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace
from langchain_chroma import Chroma
from langchain_core.tools import tool
import polars as pl
from pydantic import BaseModel
import matplotlib.pyplot as plt
import seaborn as sns

from BT_Thuc_Tap.Class.AgentState import AgentState

load_dotenv()

hf_endpoint = HuggingFaceEndpoint(
    repo_id='Qwen/Qwen2.5-7B-Instruct',
)

llm = ChatHuggingFace(llm=hf_endpoint) 
    
class EDAInsight(BaseModel):
    metric_name: str
    value: float
    n_rows: int
    chart_path: Optional[str] = None
    confidence_note: Optional[str] = None

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
        - Unique column values, mode, count of distinct categories, count of null values in our variable
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
 
@tool
def draw_graph(cols: List[str], file_path: str) -> str:
    """
    Apply this tool to draw graph for user using columns name and dataset file_path.

    Args:
        cols (List[str]): column names
        metadata (List[str]): column metadata
        file_path (str): dataset file path

    """
    lf = pl.scan_csv(file_path)
    schema = lf.collect_schema()
    
    NUMERIC_TYPES = (pl.Int8, pl.Int16, pl.Int32, pl.Int64, pl.Float32, pl.Float64, 
                     pl.UInt8, pl.UInt16, pl.UInt32, pl.UInt64)
    CAT_TYPES = (pl.Categorical, pl.String, pl.Enum)

    df_polars = lf.select([pl.col(c) for c in cols]).collect().drop_nulls()
    df = df_polars.to_pandas()
    
    plt.figure(figsize=(10, 6))

    if len(cols) == 1:
        col = cols[0]
        if schema[col] in CAT_TYPES:
            sns.countplot(data=df, x=col)
            plt.title(f"Count distribution of {col}")
            plt.xticks(rotation=45)
            
        elif schema[col] in NUMERIC_TYPES:
            sns.histplot(data=df, x=col, kde=True, color="blue")
            plt.title(f"Data distribution of {col}")

    elif len(cols) == 2:
        c1, c2 = cols[0], cols[1]
        t1, t2 = schema[c1], schema[c2]
        
        if t1 in NUMERIC_TYPES and t2 in NUMERIC_TYPES:
            sns.scatterplot(data=df, x=c1, y=c2, alpha=0.6)
            plt.title(f"Correlation between {c1} and {c2}")
            
        elif t1 in CAT_TYPES and t2 in NUMERIC_TYPES:
            sns.boxplot(data=df, x=c1, y=c2)
            plt.title(f"Distribution of {c2} across {c1}")
            
        elif t1 in NUMERIC_TYPES and t2 in CAT_TYPES:
            sns.boxplot(data=df, x=c2, y=c1)
            plt.title(f"Distribution of {c1} across {c2}")

    elif len(cols) == 3:
        num_cols = [c for c in cols if schema[c] in NUMERIC_TYPES]
        cat_cols = [c for c in cols if schema[c] in CAT_TYPES]
        
        if len(num_cols) == 2 and len(cat_cols) == 1:
            sns.scatterplot(data=df, x=num_cols[0], y=num_cols[1], hue=cat_cols[0])
            plt.title(f"Correlation between {num_cols[0]} and {num_cols[1]}, grouped by {cat_cols[0]}")
            
        elif len(num_cols) == 3:
            sns.scatterplot(data=df, x=num_cols[0], y=num_cols[1], size=num_cols[2], sizes=(20, 400), alpha=0.5)
            plt.title(f"Bubble chart: X={num_cols[0]}, Y={num_cols[1]}, Size={num_cols[2]}")

    plt.tight_layout()
    file_name = "eda_output.png"
    plt.savefig(file_name)
    plt.close()
    
    return f"Graph successfully drawn and saved at {file_name}"
    
eda_tools = [profile_dataset, univariate_analyst_numeric, univariate_analyst_cat, draw_graph]
eda_llm = llm.bind_tools(tools=eda_tools)
eda_tools_dict = {eda_tool.name: eda_tool for eda_tool in eda_tools}

def eda_agent_node(state: AgentState):
    response = eda_llm.invoke(state["messages"])
    return {"messages": [response]}


def propose_insight_node(state:AgentState) -> AgentState:
    messages = state['messages']
    system_prompt = SystemMessage(
        content="""
        You are an Exploratory Data Analysis (EDA) INSIGHT agent. You do NOT execute any data transformation or cleaning actions.
        
        Required procedure:
        1. Always call the profiling or univariate tools first to understand the dataset's schema, 
        distributions, and basic statistics.
        2. Analyze the data to extract the required statistics on the stated column.
        3. Once you have gathered sufficient insights, stop calling tools. Summarize your key findings 
        in plain text and suggest the most impactful visualizations (e.g., count distributions, correlations, box plots) 
        to represent these insights.
        """
    )
    response = eda_llm.invoke([system_prompt] + messages)
    return {'messages': [response]}   

def take_action_eda(state:AgentState) -> AgentState:
    tool_calls = state['messages'][-1].tool_calls
    results = []
    for t in tool_calls:
        print(f"Calling Tool: {t['name']} with query: {t['args'].get('query', 'No query provided')}")
        
        if not t['name'] in eda_tools_dict: 
            print(f"\nTool: {t['name']} does not exist.")
            result = "Incorrect Tool Name, Please Retry and Select tool from List of Available tools."
        
        else:
            result = eda_tools_dict[t['name']].invoke(t['args'])
            print(f"Result length: {len(str(result))}")
            
        results.append(ToolMessage(tool_call_id=t['id'], name=t['name'], content=str(result)))

    print("Tools Execution Complete. Back to the supervisor!")
    return {'messages': results}

def route_tool_or_finish(state) -> Literal["eda_tools", 'propose_insight']: #type:ignore
    last_msg = state["messages"][-1]
    if getattr(last_msg, "tool_calls", None):
        return "eda_tools"
    return 'propose_insight'

eda_graph = StateGraph(AgentState)
eda_graph.add_node('eda_agent', eda_agent_node)
eda_graph.add_node('eda_tools', take_action_eda)
eda_graph.add_node('propose_insight', propose_insight_node)

eda_graph.add_edge(START, "eda_agent")
eda_graph.add_conditional_edges(
    "eda_agent",
    route_tool_or_finish,
    {"eda_tools": "eda_tools", "propose_insight": 'propose_insight'},
)
eda_graph.add_edge("propose_insight", END)
eda_graph.add_edge("eda_tools", "eda_agent")

eda = eda_graph.compile()