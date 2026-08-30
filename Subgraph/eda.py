from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from typing import List, Literal, Annotated
from langchain_core.messages import SystemMessage, ToolMessage, HumanMessage
from langchain_deepseek import ChatDeepSeek
from langchain_core.tools import tool, InjectedToolCallId
from langgraph.prebuilt import ToolNode
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from langgraph.types import Command
import matplotlib

from Class.AgentState import AgentState
from Class.EDAInsight import EDAInsight

matplotlib.use('Agg') 
load_dotenv()

llm = ChatDeepSeek(model="deepseek-v4-flash")
    
def read_df(file_path: str, file_format: str) -> pd.DataFrame:
    if file_format == "csv":
        df = pd.read_csv(file_path)
    elif file_format == "parquet":
        df = pd.read_parquet(file_path)
    elif file_format == "json":
        df = pd.read_json(file_path, lines=True)
    else:
        raise ValueError(f"Don't support {file_format}")
    return df

@tool
def univariate_analyst_numeric(file_path: str, file_format: str, column: str, group_by: str, tool_call_id: Annotated[str, InjectedToolCallId]) -> str:
    """
    Apply this tool only to numeric data columns to extract statistical analysis containing:
        - Measures central tendency (mean, median) to find the typical value.
        - Measures dispersion (range, variance, standard deviation) to see how data spreads.
        - Detects patterns like skewness or outliers that affect data interpretation.

    Args:
        file_path (str): path to the dataset file
        column (str): name of the numeric column to analyze
        group_by (str): name of the column to group by before analysis (e.g., 'line_item_canonical' or 'symbol'). Use an empty string '' if no grouping is needed.

    Returns:
        Update the univariate field in AgentState with the dictionary containing value required
    """
    df = read_df(file_path, file_format)

    if column not in df.columns:
        return f"'{column}' not found in dataset."

    if not pd.api.types.is_numeric_dtype(df[column]):
        return f"'{column}' is not numeric (dtype={df[column].dtype}). Use a categorical analysis tool instead."

    if group_by and group_by in df.columns:
        res_list = []
        for name, group in df.groupby(group_by):
            series = group[column]
            if series.count() == 0:
                continue
            mean_val = series.mean()
            median_val = series.median()
            min_val = series.min()
            max_val = series.max()
            var_val = series.var()
            std_val = series.std()
            skew_val = series.skew()
            q1 = series.quantile(0.25)
            q3 = series.quantile(0.75)
            null_count = int(series.isnull().sum())
            count_val = int(series.count())

            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr

            outlier_count = int(((series < lower_bound) | (series > upper_bound)).sum())

            if skew_val is None or pd.isna(skew_val):
                skew_desc = "Unidentified"
            elif abs(skew_val) < 0.5:
                skew_desc = "approximately symmetric"
            elif skew_val > 0.5:
                skew_desc = "right-skewed"
            else:
                skew_desc = "left-skewed / negative skew"

            range_val = max_val - min_val
            
            res = {
                "group": str(name),
                "column": column,
                "valid_values": count_val,
                "null_values": null_count,
                "mean": round(float(mean_val), 4),
                "median": round(float(median_val), 4),
                "range": round(float(range_val), 4),
                "min": round(float(min_val), 4),
                "max": round(float(max_val), 4),
                "variance": round(float(var_val) if not pd.isna(var_val) else 0.0, 4),
                "std_dev": round(float(std_val) if not pd.isna(std_val) else 0.0, 4),
                "iqr": round(float(iqr), 4),
                "q1": round(float(q1), 4),
                "q3": round(float(q3), 4),
                "skewness": round(float(skew_val) if not pd.isna(skew_val) else 0.0, 4),
                "skewness_description": skew_desc,
                "outliers_count": outlier_count,
                "lower_bound": round(float(lower_bound), 4),
                "upper_bound": round(float(upper_bound), 4)
            }
            res_list.append(res)
        
        return Command(update={"univariate": res_list, "messages": [ToolMessage(content=str(res_list), tool_call_id=tool_call_id)]})
    else:
        series = df[column]
        mean_val = series.mean()
        median_val = series.median()
        min_val = series.min()
        max_val = series.max()
        var_val = series.var()
        std_val = series.std()
        skew_val = series.skew()
        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        null_count = int(series.isnull().sum())
        count_val = int(series.count())

        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr

        outlier_count = int(((series < lower_bound) | (series > upper_bound)).sum())

        if skew_val is None or pd.isna(skew_val):
            skew_desc = "Unidentified"
        elif abs(skew_val) < 0.5:
            skew_desc = "approximately symmetric"
        elif skew_val > 0.5:
            skew_desc = "right-skewed"
        else:
            skew_desc = "left-skewed / negative skew"

        range_val = max_val - min_val
        
        res = {
            "column": column,
            "valid_values": count_val,
            "null_values": null_count,
            "mean": round(float(mean_val), 4),
            "median": round(float(median_val), 4),
            "range": round(float(range_val), 4),
            "min": round(float(min_val), 4),
            "max": round(float(max_val), 4),
            "variance": round(float(var_val) if not pd.isna(var_val) else 0.0, 4),
            "std_dev": round(float(std_val) if not pd.isna(std_val) else 0.0, 4),
            "iqr": round(float(iqr), 4),
            "q1": round(float(q1), 4),
            "q3": round(float(q3), 4),
            "skewness": round(float(skew_val) if not pd.isna(skew_val) else 0.0, 4),
            "skewness_description": skew_desc,
            "outliers_count": outlier_count,
            "lower_bound": round(float(lower_bound), 4),
            "upper_bound": round(float(upper_bound), 4)
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
    df = read_df(file_path, file_format)

    if column not in df.columns:
        return f"'{column}' not found in dataset."

    dtype = df[column].dtype
    if pd.api.types.is_numeric_dtype(dtype) and not pd.api.types.is_categorical_dtype(dtype):
        return f"'{column}' is not a nominal/categorical type (dtype={dtype}). Use a numeric analysis tool instead."
    
    series = df[column]
    mode_series = series.dropna().mode()
    modes = mode_series.tolist()

    n_unique = int(series.dropna().nunique())
    valid_count = int(series.notna().sum())
    null_count = int(series.isna().sum())
    total_count = len(df)

    # Build frequency table
    value_counts = series.value_counts(dropna=False).reset_index()
    value_counts.columns = ["Column_value", "Value_count"]
    value_counts["Frequency"] = value_counts["Value_count"] / total_count
    value_counts["Percentage"] = value_counts["Frequency"] * 100
    value_counts = value_counts.sort_values("Value_count", ascending=False)

    valid_df = value_counts[value_counts["Column_value"].notna()]
    null_df = value_counts[value_counts["Column_value"].isna()]

    valid_str = valid_df.to_string(index=False) if not valid_df.empty else "No valid data found."
    null_str = null_df.to_string(index=False) if not null_df.empty else "No missing values."

    if not modes:
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
    df = read_df(file_path, file_format)
    
    invalid_cols = [c for c in cols if c not in df.columns]
    if invalid_cols:
        return Command(update={"messages": [ToolMessage(content=f"Columns {invalid_cols} not found in dataset schema. Valid columns: {df.columns.tolist()}", tool_call_id=tool_call_id)]})

    def is_numeric(col):
        return pd.api.types.is_numeric_dtype(df[col])
    
    def is_categorical(col):
        return pd.api.types.is_string_dtype(df[col]) or pd.api.types.is_categorical_dtype(df[col])

    df_plot = df[cols].dropna()
    
    plt.figure(figsize=(10, 6))

    if len(cols) == 1:
        col = cols[0]
        if is_categorical(col):
            sns.countplot(data=df_plot, x=col)
            plt.title(f"Count distribution of {col}")
            plt.xticks(rotation=45)
            
        elif is_numeric(col):
            sns.histplot(data=df_plot, x=col, kde=True, color="blue")
            plt.title(f"Data distribution of {col}")

    elif len(cols) == 2:
        c1, c2 = cols[0], cols[1]
        
        if is_numeric(c1) and is_numeric(c2):
            sns.scatterplot(data=df_plot, x=c1, y=c2, alpha=0.6)
            plt.title(f"Correlation between {c1} and {c2}")
            
        elif is_categorical(c1) and is_numeric(c2):
            sns.boxplot(data=df_plot, x=c1, y=c2)
            plt.title(f"Distribution of {c2} across {c1}")
            
        elif is_numeric(c1) and is_categorical(c2):
            sns.boxplot(data=df_plot, x=c2, y=c1)
            plt.title(f"Distribution of {c1} across {c2}")

    elif len(cols) == 3:
        num_cols = [c for c in cols if is_numeric(c)]
        cat_cols = [c for c in cols if is_categorical(c)]
        
        if len(num_cols) == 2 and len(cat_cols) == 1:
            sns.scatterplot(data=df_plot, x=num_cols[0], y=num_cols[1], hue=cat_cols[0])
            plt.title(f"Correlation between {num_cols[0]} and {num_cols[1]}, grouped by {cat_cols[0]}")
            
        elif len(num_cols) == 3:
            sns.scatterplot(data=df_plot, x=num_cols[0], y=num_cols[1], size=num_cols[2], sizes=(20, 400), alpha=0.5)
            plt.title(f"Bubble chart: X={num_cols[0]}, Y={num_cols[1]}, Size={num_cols[2]}")

    plt.tight_layout()
    temp = "" 
    for col in cols:
        temp += (col + '_')
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
    covered_cols = [[a.column, a.line_item_canonical, list(a.metric_value.keys())] for a in existing_actions]
    file_path = state.get('file_path', '')
    file_format = state.get('file_format', 'csv')
    dataset_profile = state.get('dataset_profile', {})
    valid_cols = dataset_profile.get('columns', [])
    if not valid_cols and file_path:
        try:
            valid_cols = read_df(file_path, file_format).columns.tolist()
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
        IMPORTANT: If analyzing long-format financial data, you MUST use `group_by='line_item_canonical'` in `univariate_analyst_numeric` tool to get statistics per line item. Analyzing the 'value' column globally is meaningless.
        3. Look at the insights already covered in 'Already proposed insights' below — do NOT propose 
        an insight for a (column, line_item_canonical, metric) tuple that already has one, unless explicitly asked to redo it.
        4. Pick exactly ONE remaining column/metric (and specific line_item_canonical if applicable) with the most impactful unresolved insight 
        (central tendency, dispersion, distribution shape, correlation, etc.) and propose a single 
        EDAInsight for it, including a suggested visualization if relevant.
        5. If every meaningful insight has already been proposed, return: {{"column": "none", "metric_value": {{"NONE": 0.0}}}}
        """
    )

    structured_llm = llm.with_structured_output(EDAInsight, method="json_mode")
    res = structured_llm.invoke(
        [system_prompt] + 
        [HumanMessage(content=f"Valid dataset columns: {valid_cols}")] + 
        messages + [HumanMessage(content=(
            f"""Already proposed insights: {covered_cols}\n
            Summarize as JSON matching schema for ONE column with metric_name and value appended to metric_value dict only.\n
            {{"column":str, "line_item_canonical":str|null, "metric_value":Dict[str:float]}}
            """
        ))]
    )

    summary = "\n".join(f"- {a.column} ({a.line_item_canonical}): {list(a.metric_value.keys())}" for a in existing_actions) 
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

def route_after_propose(state: AgentState) -> Literal["eda_agent", "__end__"]:
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