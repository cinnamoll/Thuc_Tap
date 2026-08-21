from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from typing import List, Literal, Annotated
from langchain_core.messages import SystemMessage, ToolMessage, HumanMessage
from langchain_deepseek import ChatDeepSeek
from langchain_core.tools import tool, InjectedToolCallId
from langgraph.prebuilt import ToolNode
import polars as pl
import matplotlib.pyplot as plt
import seaborn as sns
from langgraph.types import Command
import matplotlib

from Class.AgentState import AgentState
from Class.EDAInsight import EDAInsight

matplotlib.use('Agg') 
load_dotenv()

llm = ChatDeepSeek(model="deepseek-v4-flash")
    
def get_lf(file_path: str, file_format: str):
    if file_format == "csv":
        lf = pl.scan_csv(file_path)
    elif file_format == "parquet":
        lf = pl.scan_parquet(file_path)
    elif file_format == "json":
        lf = pl.scan_ndjson(file_path)
    else:
        raise ValueError(f"Don't support {file_format}")
    return lf

@tool
def univariate_analyst_numeric(file_path: str, file_format: str, column: str, tool_call_id: Annotated[str, InjectedToolCallId]) -> str:
    """
    Apply this tool only to numeric data columns to extract statistical analysis containing:
        - Measures central tendency (mean, median) to find the typical value.
        - Measures dispersion (range, variance, standard deviation) to see how data spreads.
        - Detects patterns like skewness or outliers that affect data interpretation.

    Args:
        file_path (str): path to the dataset file
        column (str): name of the numeric column to analyze

    Returns:
        Update the univariate field in AgentState with the dictionary containing value required
    """
    lf = get_lf(file_path, file_format)
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
        skew_desc = "Unidentified"
    elif abs(skew) < 0.5:
        skew_desc = "approximately symmetric"
    elif skew > 0.5:
        skew_desc = "right-skewed"
    else:
        skew_desc = "left-skewed / negative skew"

    range_val = stats["max"] - stats["min"]
    
    res = {
        "column": column,
        "valid_values": stats['count'],
        "null_values": stats['null_count'],
        "mean": round(stats['mean'], 4),
        "median": round(stats['median'], 4),
        "range": round(range_val, 4),
        "min": round(stats['min'], 4),
        "max": round(stats['max'], 4),
        "variance": round(stats['variance'], 4),
        "std_dev": round(stats['std'], 4),
        "iqr": round(iqr, 4),
        "q1": round(q1, 4),
        "q3": round(q3, 4),
        "skewness": round(skew, 4),
        "skewness_description": skew_desc,
        "outliers_count": outlier_count,
        "lower_bound": round(lower_bound, 4),
        "upper_bound": round(upper_bound, 4)
    }
    
    return Command(update={"univariate": [res], "messages": [ToolMessage(content=str(res), tool_call_id=tool_call_id)]})
    
@tool
def univariate_analyst_cat(file_path: str, file_format: str, column: str, tool_call_id: Annotated[str, InjectedToolCallId]) -> str:
    """
    Apply this tool only to nominal data columns to extract statistical analysis containing:
        - Unique column values, mode, count of distinct categories, count of null values in our variable
        - Generate a frequency table, containing 6 columns [Column_value, Value_count, Frequency, Percentage]
        divided into 2 parts of Valid values and Missing Values

    Args:
        file_path (str): path to the dataset file
        column (str): name of the nominal column to analyze

    Returns:
        Update the univariate field in AgentState with the dictionary containing value required
    """
    lf = get_lf(file_path, file_format)
    schema = lf.collect_schema()

    if column not in schema.names():
        return f"'{column}' not found in dataset."

    dtype = schema[column]
    if dtype not in (pl.Categorical, pl.String) and not isinstance(dtype, pl.Enum):
        return f"'{column}' is not a nominal/categorical type (dtype={dtype}). Use a numeric analysis tool instead."
    
    df = lf.select(pl.col(column)).collect()
    
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
    null_df = freq_table.filter(pl.col("Column_value").is_null())

    with pl.Config(tbl_rows=valid_df.height if valid_df.height > 0 else 1, tbl_cols=4):
        valid_str = str(valid_df) if not valid_df.is_empty() else "No valid data found."
        
    with pl.Config(tbl_rows=null_df.height if null_df.height > 0 else 1, tbl_cols=4):
        null_str = str(null_df) if not null_df.is_empty() else "No missing values."

    if modes.is_empty():
        mode_str = None
    else:
        mode_str = ', '.join(map(str, modes)) 
    
    res = {
        "valid_count": valid_count,
        "valid_values": valid_str,
        "null_count": null_count,
        "null_values": null_str,
        "n_unique": n_unique,
        "mode": mode_str
    }
    
    return Command(update={"univariate": [res],"messages": [ToolMessage(content=str(res), tool_call_id=tool_call_id)]})
 
@tool
def draw_graph(file_path: str, file_format: str, cols: List[str], tool_call_id: Annotated[str, InjectedToolCallId]) -> str:
    """
    Apply this tool to draw graph for user using columns name and dataset file_path.

    Args:
        cols (List[str]): column names
        metadata (List[str]): column metadata
        file_path (str): dataset file path

    """
    lf = get_lf(file_path, file_format)
    schema = lf.collect_schema()
    
    invalid_cols = [c for c in cols if c not in schema.names()]
    if invalid_cols:
        return Command(update={"messages": [ToolMessage(content=f"Columns {invalid_cols} not found in dataset schema. Valid columns: {list(schema.names())}", tool_call_id=tool_call_id)]})

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
    temp = "" 
    for col in cols:
        temp += (col + ' ')
    file_name = f"{temp}_eda_output.png"
    plt.savefig(file_name)
    plt.close()
    
    return Command(update={
        "chart_paths": [file_name], 
        "messages": [ToolMessage(content=f"Graph successfully drawn and saved at {file_name}", tool_call_id=tool_call_id)]
    })
    
eda_tools = [univariate_analyst_numeric, univariate_analyst_cat, draw_graph]
tool_node = ToolNode(eda_tools)
eda_llm = llm.bind_tools(tools=eda_tools)
eda_tools_dict = {eda_tool.name: eda_tool for eda_tool in eda_tools}

def eda_agent_node(state: AgentState):
    response = eda_llm.invoke(state["messages"])
    return {"messages": [response]}

def propose_insight_node(state: AgentState) -> AgentState:
    messages = state['messages']
    existing_actions = state.get('pending_insight', [])
    covered_cols = [[a.column, a.metric_value] for a in existing_actions]
    file_path = state.get('file_path', '')
    file_format = state.get('file_format', 'csv')
    dataset_profile = state.get('dataset_profile', {})
    valid_cols = dataset_profile.get('columns', [])
    if not valid_cols and file_path:
        try:
            valid_cols = list(get_lf(file_path, file_format).collect_schema().names())
        except Exception:
            valid_cols = []

    system_prompt = SystemMessage(
        content=f"""
        You are an Exploratory Data Analysis (EDA) INSIGHT agent. You do NOT execute any data 
        transformation or cleaning actions.
        Required procedure:
        1. Valid columns in dataset: {valid_cols}. You MUST select 'column' strictly from this list. Do NOT invent non-existent column names (e.g. 'id').
        2. Always call the profiling or univariate tools first to understand the dataset's schema, 
        distributions, and basic statistics.
        3. Look at the insights already covered in 'Already proposed insights' below — do NOT propose 
        an insight for a (column, metric) pair that already has one, unless explicitly asked to redo it.
        4. Pick exactly ONE remaining column/metric with the most impactful unresolved insight 
        (central tendency, dispersion, distribution shape, correlation, etc.) and propose a single 
        EDAInsight for it, including a suggested visualization if relevant.
        5. If every meaningful insight has already been proposed, return: {"column": "none", "metric_value": {"NONE": 0.0}}
        """
    )

    structured_llm = llm.with_structured_output(EDAInsight, method="json_mode")
    res = structured_llm.invoke(
        [system_prompt] + 
        [HumanMessage(content=f"Valid dataset columns: {valid_cols}")] + 
        messages + [HumanMessage(content=(
            f"""Already proposed insights: {covered_cols}\n
            Summarize as JSON matching schema for ONE column with metric_name and value appended to metric_value dict only.\n
            {{"column":str, "metric_value":Dict[str:float]}}
            """
        ))]
    )

    summary = "\n".join(f"- {a.column}: {list(a.metric_value.keys())}" for a in existing_actions) 
    if list(res.metric_value.keys()) == ["NONE"]:
        return Command(update={"eda_done": True})

    if state.get("chart_paths") and not res.chart_paths:
        res.chart_paths = state.get("chart_paths") 

    return Command(update={
        "pending_insight": existing_actions + [res],  
        "messages": [HumanMessage(content=summary)]
    })

def route_tool_or_finish(state) -> Literal["eda_tools", 'propose_insight']:
    last_msg = state["messages"][-1]
    if getattr(last_msg, "tool_calls", None):
        return "eda_tools"
    return 'propose_insight'

def route_after_propose(state: AgentState) -> Literal["eda_agent", END]: #type:ignore
    if state.get("eda_done") == True:
        return END
    return "eda_agent" 

eda_graph = StateGraph(AgentState)
eda_graph.add_node('eda_agent', eda_agent_node)
eda_graph.add_node('eda_tools', tool_node)
eda_graph.add_node('propose_insight', propose_insight_node)

eda_graph.add_edge(START, "eda_agent")
eda_graph.add_conditional_edges(
    "eda_agent",
    route_tool_or_finish,
    {
        "eda_tools": "eda_tools", 
        "propose_insight": 'propose_insight'
    }
)
eda_graph.add_conditional_edges(
    "propose_insight",
    route_after_propose,
    {
        "eda_agent": "eda_agent",
        END: END,
    },
)
eda_graph.add_edge("eda_tools", "eda_agent")
eda = eda_graph.compile()

# img = eda.get_graph().draw_mermaid_png()
# with open('Subgraph_Img/eda_image.png', 'wb') as f:
#     f.write(img)