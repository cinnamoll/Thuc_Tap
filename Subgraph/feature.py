import os
import uuid
import json
import pandas as pd
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from typing import Literal, Annotated
from langchain_core.messages import SystemMessage, ToolMessage, HumanMessage
from langchain_deepseek import ChatDeepSeek
from langgraph.prebuilt import ToolNode
from langchain_core.tools import tool, InjectedToolCallId
import re
from langgraph.types import Command

from Class.AgentState import AgentState
from Class.EngineeringAction import EngineeringAction, BinningType, FinancialFeatureType

load_dotenv()
llm = ChatDeepSeek(model="deepseek-v4-flash")

@tool
def preview_binning_standard_tool(file_path: str, column: str, encode: BinningType, tool_call_id: Annotated[str, InjectedToolCallId], n_bin: int=10, length: int=20) -> str:
    """
    Apply this tool only to continuos data columns to binned / standardized:
        - Use result from univariate_analyst_ as input to suggest binning plans

    Args:
        file_path (str): path to the dataset file
        column (str): name of the continuos column to analyze
        n_bin (str): number of bins
        encode (EngineeringType.BINNING): type of binning to use
        length (int): length of binning dataframe head

    Returns:
        - A new Binned column head
    """
    
    if not file_path or not os.path.exists(file_path):
        return Command(update={"messages": [ToolMessage(content=f"Dataset file '{file_path}' not found.", tool_call_id=tool_call_id)]})
    df = pd.read_csv(file_path)
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
    else: 
        return "Unsupported binning type" 
    
    res = {"Target Column": column, "Method": encode, f"First {length} rows": new_df.to_string(index=False)}
    
    return Command(update={"preview_feature": res, "messages": [ToolMessage(content="Binning/Standardize complete " + str(res), tool_call_id=tool_call_id)]})

@tool 
def preview_growth_rate_tool(file_path: str, column: str, group_by: str, time_col: str, tool_call_id: Annotated[str, InjectedToolCallId], length: int = 20) -> str:
    """
    Preview YoY/QoQ growth rate computation for a numeric column grouped by line items.

    Args:
        file_path (str): path to the dataset file
        column (str): name of the numeric value column
        group_by (str): grouping column (e.g. 'line_item_canonical')
        time_col (str): time period column (e.g. 'fiscal_year')
        length (int): number of rows to preview

    Returns:
        Preview of growth rate computation
    """
    df = pd.read_csv(file_path)
    for c in [column, group_by, time_col]:
        if c not in df.columns:
            return f"'{c}' not found in dataset."

    df = df.sort_values([group_by, time_col])
    df[f"{column}_growth_rate"] = df.groupby(group_by)[column].pct_change() * 100
    preview = df[[group_by, time_col, column, f"{column}_growth_rate"]].head(length)

    res = {"Target Column": column, "Method": "derive_growth_rate", f"First {length} rows": preview.to_string(index=False)}
    return Command(update={"preview_feature": res, "messages": [ToolMessage(content="Growth rate preview: " + str(res), tool_call_id=tool_call_id)]})

@tool
def preview_lag_feature_tool(file_path: str, column: str, group_by: str, time_col: str, tool_call_id: Annotated[str, InjectedToolCallId], length: int = 20) -> str:
    """
    Preview lag feature (previous period value) for a column grouped by line items.

    Args:
        file_path (str): path to the dataset file
        column (str): name of the value column
        group_by (str): grouping column (e.g. 'line_item_canonical')
        time_col (str): time period column
        length (int): number of rows to preview

    Returns:
        Preview of lag feature
    """
    df = pd.read_csv(file_path)
    for c in [column, group_by, time_col]:
        if c not in df.columns:
            return f"'{c}' not found in dataset."

    df = df.sort_values([group_by, time_col])
    df[f"{column}_lag_1"] = df.groupby(group_by)[column].shift(1)
    preview = df[[group_by, time_col, column, f"{column}_lag_1"]].head(length)

    res = {"Target Column": column, "Method": "lag_feature", f"First {length} rows": preview.to_string(index=False)}
    return Command(update={"preview_feature": res, "messages": [ToolMessage(content="Lag feature preview: " + str(res), tool_call_id=tool_call_id)]})

@tool
def preview_common_size_tool(file_path: str, column: str, group_by: str, base_item: str, time_col: str, tool_call_id: Annotated[str, InjectedToolCallId], length: int = 20) -> str:
    """
    Preview common-size transformation: express each value as % of a base item per period.

    Args:
        file_path (str): path to the dataset file
        column (str): value column
        group_by (str): grouping column (e.g. 'line_item_canonical')
        base_item (str): line item to use as 100% base (e.g. 'tong_tai_san')
        time_col (str): time period column
        length (int): number of rows to preview

    Returns:
        Preview of common-size percentages
    """
    df = pd.read_csv(file_path)
    for c in [column, group_by, time_col]:
        if c not in df.columns:
            return f"'{c}' not found in dataset."

    results = []
    for period_val in df[time_col].unique():
        period_df = df[df[time_col] == period_val]
        base_rows = period_df[period_df[group_by] == base_item]
        base_val = base_rows[column].sum() if not base_rows.empty else 0.0
        for _, row in period_df.iterrows():
            pct = (row[column] / base_val * 100) if base_val != 0 else 0.0
            results.append({group_by: row[group_by], time_col: period_val, column: row[column], "common_size_pct": round(pct, 2)})

    preview_df = pd.DataFrame(results).head(length)
    res = {"Target Column": column, "Method": "common_size_transform", f"First {length} rows": preview_df.to_string(index=False)}
    return Command(update={"preview_feature": res, "messages": [ToolMessage(content="Common-size preview: " + str(res), tool_call_id=tool_call_id)]})

@tool
def preview_cross_statement_join_tool(file_path: str, join_key: str, tool_call_id: Annotated[str, InjectedToolCallId], length: int = 20) -> str:
    """
    Preview cross-statement join readiness. Shows how data would be structured after joining
    BS+IS+CF by period key.

    Args:
        file_path (str): path to the dataset file
        join_key (str): the period key column to join on (e.g. 'fiscal_year')
        length (int): number of rows to preview

    Returns:
        Preview of join structure
    """
    df = pd.read_csv(file_path)
    if join_key not in df.columns:
        return f"'{join_key}' not found in dataset."

    if "statement_type" in df.columns:
        pivot = df.groupby([join_key, "statement_type"]).size().reset_index(name="count")
        preview = pivot.head(length)
    else:
        preview = df[[join_key]].drop_duplicates().head(length)
        preview["note"] = "No statement_type column — will be tagged during execution"

    res = {"Join Key": join_key, "Method": "cross_statement_join", f"First {length} rows": preview.to_string(index=False)}
    return Command(update={"preview_feature": res, "messages": [ToolMessage(content="Cross-statement join preview: " + str(res), tool_call_id=tool_call_id)]})

feature_tools = [preview_binning_standard_tool, preview_growth_rate_tool, preview_lag_feature_tool, preview_common_size_tool, preview_cross_statement_join_tool]
tool_node = ToolNode(feature_tools)
feature_llm = llm.bind_tools(tools=feature_tools)
feature_tools_dict = {feature_tool.name: feature_tool for feature_tool in feature_tools}

def feature_agent_node(state: AgentState):
    file_path = state.get('file_path', '')
    file_path_prompt = SystemMessage(
        content=f"The target dataset file_path is: '{file_path}'. "
                f"When calling tools, you MUST pass file_path='{file_path}'."
    )
    response = feature_llm.invoke([file_path_prompt] + list(state['messages']))
    return {'messages': [response]} 

def parse_json_feature(raw_content: str) -> EngineeringAction:
    text = raw_content.strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        text = match.group(0)
    try:
        data = json.loads(text)
        return EngineeringAction.model_validate(data)
    except Exception:
        return EngineeringAction(actionType=FinancialFeatureType.NONE)

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
            valid_cols = pd.read_csv(file_path).columns.tolist()
        except Exception:
            valid_cols = []

    system_prompt = SystemMessage(
        content=f"""
        You are a data feature engineering INVESTIGATION agent. You do NOT execute any transformation
        action.
        Required procedure:
        1. Valid columns in dataset: {valid_cols}. You MUST select 'column' strictly from this list. Do NOT invent non-existent column names (e.g. 'id').
        2. Call the standardization tool for numerical columns and preview the column(s) head
        after transformation.
        3. For financial time-series data, prefer the financial feature tools:
           - `preview_growth_rate_tool`: YoY/QoQ growth rates per line item
           - `preview_lag_feature_tool`: previous period values
           - `preview_common_size_tool`: % of total assets/revenue
           - `preview_cross_statement_join_tool`: prepare join of BS+IS+CF by period key
        4. Look at the actions already covered in 'Already proposed actions' below — do NOT propose
        an action for a target that already has one, unless explicitly asked to redo it.
        5. Pick exactly ONE remaining column/transformation with the most impactful unresolved issue
        and propose a single EngineeringAction for it.
        6. If every column has already been adequately transformed, or there is nothing further worth
        proposing, return a JSON object with "actionType": "none" to signal completion.

        IMPORTANT RULES FOR FINANCIAL DATA (Long-format):
        - DO NOT propose standard financial ratios (e.g. ROE, ROA, Debt-to-Equity). These are handled by a dedicated `ratio_trend_engine`.
        - Binning (equal_width/quantile) are DISALLOWED on financial data.
        - BinningType: only 'standardize' is valid for accounting data.
        - Prefer FinancialFeatureType actions: derive_growth_rate, common_size_transform, lag_feature, cross_statement_join.

        Valid actionType values: "standardize", "derive_growth_rate", "common_size_transform", "lag_feature", "cross_statement_join", "none"
        """
    )
    response = llm.invoke(
        [system_prompt] +
        [HumanMessage(content=f"Valid dataset columns: {valid_cols}")] +
        messages + [HumanMessage(content=
            f"""Already proposed actions (column, line_item_canonical, actionType): {covered_actions}
            Summarize as raw JSON matching schema for ONE action only:
            Example JSON format:
            {{"file_path": "{file_path}", "file_format": "{file_format}", "reason": "feature engineering", "column": "value", "line_item_canonical": "tong_tai_san", "statement_type": "balance_sheet", "period": "2024Q4", "fiscal_year": 2024, "rows_affected": 0, "rows_ratio": 0.0, "risk_level": "low", "actionType": "none", "n_bin": 10, "base_item": null, "time_column": null}}
            Preview the column for user using {state.get('preview_feature', '')}
            """
        )]
    )
    res = parse_json_feature(getattr(response, "content", ""))
    if not res.file_path:
        res.file_path = file_path
    if not res.file_format:
        res.file_format = file_format

    all_actions = existing_actions + [res]
    summary = "\n".join(f"- {a.column} ({a.line_item_canonical}): {a.actionType}" for a in all_actions)
    if res.actionType in (BinningType.NONE, FinancialFeatureType.NONE):
        return Command(update={"engineer_done": True})

    return Command(update={
        "pending_engineering": all_actions,
        "messages": [HumanMessage(content=summary)]
    })

def route_tool_or_finish(state) -> Literal["feature_tools", "propose_action"]: 
    last_msg = state["messages"][-1]
    if getattr(last_msg, "tool_calls", None):
        return "feature_tools"
    return "propose_action"

def route_after_propose(state: AgentState) -> Literal["feature_agent", "__end__"]: #type:ignore
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