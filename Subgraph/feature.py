from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from typing import Literal, Annotated
from langchain_core.messages import SystemMessage, ToolMessage, HumanMessage
from langchain_deepseek import ChatDeepSeek
from langgraph.prebuilt import ToolNode
from langchain_core.tools import tool, InjectedToolCallId
import pandas as pd
from langgraph.types import Command

from Class.AgentState import AgentState
from Class.EngineeringAction import EngineeringAction, EncodingType, BinningType

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
def preview_encoding_tool(file_path: str, file_format: str, column: str, encode: EncodingType, tool_call_id: Annotated[str, InjectedToolCallId], length: int=20) -> str:
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
    
    df = read_df(file_path, file_format)

    if column not in df.columns:
        return f"'{column}' not found in dataset."

    dtype = df[column].dtype
    if pd.api.types.is_numeric_dtype(dtype) and not pd.api.types.is_categorical_dtype(dtype):
        return f"'{column}' is not a nominal/categorical type (dtype={dtype})"
    
    df = df[[column]].head(length).copy()
    
    if encode == 'frequency_encoding':
        freq_map = df[column].value_counts(normalize=True)
        encoded_df = df.copy()
        encoded_df[f'{column}_encoded'] = df[column].map(freq_map)
    elif encode == 'label_encoding':
        codes, _ = pd.factorize(df[column])
        encoded_df = df.copy()
        encoded_df[f'{column}_encoded'] = codes
    elif encode == 'ordinal_encoding':
        unique_vals = sorted(df[column].dropna().unique())
        mapping = {val: i for i, val in enumerate(unique_vals)}
        encoded_df = df.copy()
        encoded_df[f'{column}_encoded'] = df[column].map(mapping).astype('Int32')
    elif encode == 'one_hot_encoding':
        encoded_df = pd.get_dummies(df, columns=[column])
    else: 
        return "Unsupported encode type"   
    
    res = {
        "Target Column": column,
        "Method": encode,
        f"First {length} rows": encoded_df.to_string(index=False)
    }
    
    return Command(update={
        "preview_feature": res,
        "messages": [ToolMessage(content="Encoding complete " + str(res), tool_call_id=tool_call_id)]
    })

@tool
def preview_binning_standard_tool(file_path: str, file_format: str, column: str, encode: BinningType, tool_call_id: Annotated[str, InjectedToolCallId], n_bin: int=10, length: int=20) -> str:
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
    
    df = read_df(file_path, file_format)

    if column not in df.columns:
        return f"'{column}' not found in dataset."

    if not pd.api.types.is_numeric_dtype(df[column]):
        return f"'{column}' is not numeric (dtype={df[column].dtype})"
    
    df = df[[column]].head(length).copy()
    
    if encode == 'standardize':
        mean = df[column].mean()
        std = df[column].std()
        if std is not None and std > 0:
            new_df = df.copy()
            new_df[f"{column}_std"] = (df[column] - mean) / std
        else:
            return "Std is None. No binning with this column"
    elif encode == 'equal_width':
        min_val = df[column].min()
        max_val = df[column].max()
        
        step = (max_val - min_val) / n_bin
        breaks = [min_val + i * step for i in range(1, n_bin)]
        
        new_df = df.copy()
        new_df[f"{column}_binned"] = pd.cut(df[column], bins=[min_val] + breaks + [max_val], include_lowest=True)
    elif encode == 'quantile':
        new_df = df.copy()
        new_df[f"{column}_binned"] = pd.qcut(df[column], q=n_bin, duplicates='drop')
    else: 
        return "Unsupported binning type" 
    
    res = {
        "Target Column": column,
        "Method": encode,
        f"First {length} rows": new_df.to_string(index=False)
    }
    
    return Command(update={
        "preview_feature": res,
        "messages": [ToolMessage(content="Binning/Standardize complete " + str(res), tool_call_id=tool_call_id)]
    })
    

feature_tools = [preview_encoding_tool, preview_binning_standard_tool]
tool_node = ToolNode(feature_tools)
feature_llm = llm.bind_tools(tools=feature_tools)
feature_tools_dict = {feature_tool.name: feature_tool for feature_tool in feature_tools}

def feature_agent_node(state: AgentState):
    response = feature_llm.invoke(state['messages'])
    return {'messages': [response]} 

def propose_action_node(state: AgentState) -> AgentState:
    messages = state['messages']
    existing_actions = state.get('pending_engineering', [])
    covered_actions = [(a.column, a.line_item_canonical, a.actionType) for a in existing_actions]
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
        You are a data feature engineering INVESTIGATION agent. You do NOT execute any transformation 
        action.
        Required procedure:
        1. Valid columns in dataset: {valid_cols}. You MUST select 'column' strictly from this list. Do NOT invent non-existent column names (e.g. 'id').
        2. Call the encoding tool for categorical columns and preview the column(s) head after encoding; 
        call the standardization or binning tool for numerical columns and preview the column(s) head 
        after transformation.
        3. Look at the actions already covered in 'Already proposed actions' below — do NOT propose 
        an action for a target that already has one, unless explicitly asked to redo it.
        4. Pick exactly ONE remaining column/transformation with the most impactful unresolved issue 
        and propose a single EngineeringAction for it.
        5. If every column has already been adequately transformed, or there is nothing further worth 
        proposing, return a JSON object with "actionType": "none" to signal completion.
        
        IMPORTANT RULES FOR FINANCIAL DATA (Long-format):
        - DO NOT propose standard financial ratios (e.g. ROE, ROA, Debt-to-Equity). These are handled by a dedicated `ratio_trend_engine`.
        - DO NOT propose one-hot encoding for `line_item_canonical` or other metadata columns in the long-format data.
        - You SHOULD propose actions like 'binning' continuous variables according to industry thresholds, or calculating simple temporal variables (e.g. raw YoY growth).
        
        Valid actionType values: "label_encoding", "ordinal_encoding", "frequency_encoding", "one_hot_encoding", "equal_width", "quantile", "standardize", "none"
        """
    )
    structured_llm = llm.with_structured_output(EngineeringAction, method='json_mode')
    res = structured_llm.invoke(
        [system_prompt] + 
        [HumanMessage(content=f"Valid dataset columns: {valid_cols}")] + 
        messages + [HumanMessage(content=
            f"""Already proposed actions (column, line_item_canonical, actionType): {covered_actions}
            Summarize as JSON matching schema for ONE action only:
            {{"file_path": "{file_path}", "file_format": "{file_format}", "reason": str, "column": str, "line_item_canonical": str|null, "rows_affected": int | null, "rows_ratio": float | null,
                "risk_level": "low" | "medium" | "high" | null, "actionType": "label_encoding"|"ordinal_encoding"|"frequency_encoding"|"one_hot_encoding"|"equal_width"|"quantile"|"standardize"|"none", "n_bin": int}}\n
            Preview the column for user using {state.get('preview_feature', '')}
            """
        )]
    )
    if not res.file_path:
        res.file_path = file_path
    if not res.file_format:
        res.file_format = file_format

    summary = "\n".join(f"- {a.column} ({a.line_item_canonical}): {a.actionType}" for a in existing_actions)
    if res.actionType in (EncodingType.NONE, BinningType.NONE): 
        return Command(update={"engineer_done": True})

    return Command(update={
        "pending_engineering": existing_actions + [res],
        "messages": [HumanMessage(content=summary)]
    })

def route_tool_or_finish(state) -> Literal["feature_tools", "propose_action"]: 
    last_msg = state["messages"][-1]
    if getattr(last_msg, "tool_calls", None):
        return "feature_tools"
    return "propose_action"

def route_after_propose(state: AgentState) -> Literal["feature_agent", END]: #type:ignore
    if state.get("engineer_done"):
        return END
    return "feature_agent" 

feature_graph = StateGraph(AgentState)
feature_graph.add_node('feature_agent', feature_agent_node)
feature_graph.add_node('feature_tools', tool_node) 
feature_graph.add_node('propose_action', propose_action_node)

feature_graph.add_edge(START, 'feature_agent')
feature_graph.add_conditional_edges(
    "feature_agent",
    route_tool_or_finish,
    {
        "feature_tools": "feature_tools", 
        'propose_action': 'propose_action'
    }
)
feature_graph.add_conditional_edges(
    "propose_action",
    route_after_propose,
    {
        "feature_agent": "feature_agent",
        END: END,
    },
)
feature_graph.add_edge("feature_tools", "feature_agent")

feature_engineering = feature_graph.compile()

# img = feature_engineering.get_graph().draw_mermaid_png()
# with open('Subgraph_Img/feature_image.png', 'wb') as f:
#     f.write(img)