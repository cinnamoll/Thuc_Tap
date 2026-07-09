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
from langchain_core.language_models.chat_models import BaseChatModel

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


def scan_file(file_path:str, file_format: str):
    if file_format == 'csv':
        df = pl.read_csv(file_path)
    elif file_format in ['xlsx', 'xls']:
        df = pl.read_excel(file_path)
    elif file_format == 'json':
        df = pl.read_json(file_path)
    return df

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
    df = scan_file(state['file_path'], state['file_format'])
    cols = df.columns
    return cols

def extract_metadata_node(state: AgentState, llm:BaseChatModel):
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
    
@tool
def profile_dataset(file_path: str, file_format:str) -> dict:
    """
    Scan a dataset (lazy, not loading the entire dataset into RAM) and return statistics:
    dtypes, number of nulls for both numerical and categorical columns and unique values for categorical column.
    Used to detect problems before suggesting cleaning.
    """
    lf = scan_file(file_path, file_format)
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
    
def data_cleaning_node(state:AgentState, llm:BaseChatModel):
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

#eda
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
    
@tool 
def multivariate_analyst(file_path: str, column: str) -> str:
    pass

@tool
def draw_graph(
    column: str,
    metadata: str
):
    pass
    
eda_tools = [univariate_analyst_numeric, univariate_analyst_cat, multivariate_analyst, draw_graph]
eda_llm = llm.bind_tools(tools=eda_tools)

def eda_agent_node(state: AgentState):
    response = eda_llm.invoke(state["messages"])
    return {"messages": [response]}

eda_graph = StateGraph(AgentState)

eda_graph.add_node('eda_agent', eda_agent_node)
eda_graph.add_node('eda_tools', ToolNode(eda_tools))

eda_graph.add_edge(START, 'eda_agent')
eda_graph.add_edge('eda_agent', tools_condition)
eda_graph.add_edge('eda_tools', 'eda_agent')

eda = eda_graph.compile()

#feature engineering
@tool
def feature_transformation():
    pass

@tool
def encoding_tool(
    file_path: str, 
    column: str,
    action: Literal["label_encoding", "ordinal_encoding", "frequency_encoding", "one_hot_encoding"]
) -> str:
    f"""
    Apply this tool only to nominal data columns to encoding:
        - Use result from univariate_analyst_cat as input to suggest encoding plans

    Args:
        file_path (str): path to the dataset file
        column (str): name of the nominal column to analyze

    Returns:
        - A new Encoded/Binned column
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
        - Method Applied: {action.upper()}
        - New DataFrame Glimpse (First 5 rows):
        {sample_str}
    """
    
    return res

@tool
def feature_selection():
    pass

feature_tools = [feature_transformation, encoding_tool, feature_selection]
feature_llm = llm.bind_tools(tools=feature_tools)

def feature_agent_node(state: AgentState):
    response = feature_llm.invoke(state["messages"])
    return {"messages": [response]}

feature_graph = StateGraph(AgentState)

feature_graph.add_node('feature_agent', feature_agent_node)
feature_graph.add_node('eda_tools', ToolNode(feature_tools))

feature_graph.add_edge(START, 'feature_agent')
feature_graph.add_edge('feature_agent', tools_condition)
feature_graph.add_edge('feature_tools', 'feature_agent')

feature_engineering = feature_graph.compile()

# def route_supervisor_decision():
#     pass

#main graph
tools = [extract_columns, profile_dataset, apply_cleaning]  

llm = llm.bind_tools(tools=tools) 

graph = StateGraph(AgentState)
graph.add_node('extract_metadata', extract_metadata_node)
graph.add_node('clean_dataset', data_cleaning_node)
graph.add_node('tools', ToolNode(tools=tools))
graph.add_node('eda', eda)
graph.add_node('feature_engineering', feature_engineering)

graph.add_edge(START, 'extract_metadata')
graph.add_conditional_edges(
    'extract_metadata',
    tools_condition
)
graph.add_edge('tools', 'extract_metadata')

graph.add_conditional_edges(
    'extract_metadata',
    # route_supervisor_decision
    'next_step',
    {
        'Cleaning': 'cleaning',
        'EDA': 'eda',
        'Feature_engineering': 'feature_engineering',
        'FINISH': END
    }
)


app = graph.compile()

user_input = input("Enter: ")
while user_input.lower() != 'exit':
    for event in app.stream({'messages': [HumanMessage(content=user_input)]}):
        for node_name, node_state in event.items():
            print(f"\n--- Output from {node_name} ---")
            last_message = node_state['messages'][-1]
            print(last_message.content if last_message.content else "[Tool Call]")
            
    user_input = input("Enter: ")