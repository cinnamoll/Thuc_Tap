from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from typing import Literal, Annotated
from langchain_core.messages import SystemMessage, ToolMessage, HumanMessage
from langchain_deepseek import ChatDeepSeek
from langchain_core.tools import tool, InjectedToolCallId
from langgraph.prebuilt import ToolNode 
import json
import re
import pandas as pd
from langgraph.types import Command

from Class.AgentState import AgentState
from Class.CleaningAction import CleaningAction, CleaningActionType

load_dotenv()
llm = ChatDeepSeek(model="deepseek-v4-flash")

import os

@tool
def profile_dataset(file_path: str, tool_call_id: Annotated[str, InjectedToolCallId]) -> dict:
    """
    Read a dataset and return statistics:
    dtypes, number of nulls for both numerical and categorical columns and unique values for categorical column.
    Used to detect problems before suggesting cleaning.
    """
    if not file_path or not os.path.exists(file_path):
        res = {"error": f"Dataset file '{file_path}' not found."}
        return Command(update={"messages": [ToolMessage(content=str(res), tool_call_id=tool_call_id)]})

    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        res = {"error": f"Failed to read dataset file '{file_path}': {e}"}
        return Command(update={"messages": [ToolMessage(content=str(res), tool_call_id=tool_call_id)]})

    stats = {}
    for col in df.columns:
        stats[f"{col}_nulls"] = int(df[col].isnull().sum())
        stats[f"{col}_nunique"] = int(df[col].nunique())

    res = {
        "columns": df.columns.tolist(),
        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
        "stats": stats,
        "n_rows": len(df)
    }

    return Command(update={"dataset_profile": res, "messages": [ToolMessage(content=str(res), tool_call_id=tool_call_id)]})

cleaning_tools = [profile_dataset]
tool_node = ToolNode(cleaning_tools)
cleaning_llm = llm.bind_tools(cleaning_tools)
cleaning_tools_dict = {cleaning_tool.name: cleaning_tool for cleaning_tool in cleaning_tools}

def data_cleaning_node(state:AgentState):
    file_path = state.get('file_path', '')
    file_path_prompt = SystemMessage(
        content=f"The target dataset file_path is: '{file_path}'. "
                f"When calling tool 'profile_dataset', you MUST pass file_path='{file_path}'."
    )
    response = cleaning_llm.invoke([file_path_prompt] + list(state['messages']))
    return {'messages': [response]}    

def parse_json_cleaning(raw_content: str) -> CleaningAction:
    text = raw_content.strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        text = match.group(0)
    try:
        data = json.loads(text)
        return CleaningAction.model_validate(data)
    except Exception:
        return CleaningAction(actionType=CleaningActionType.NONE)

def propose_action_node(state: AgentState) -> AgentState:
    messages = state['messages']
    existing_actions = state.get('pending_cleaning', [])
    covered_actions = [(a.statement_type, a.period, a.column, a.line_item_canonical, a.actionType) for a in existing_actions]
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
        You are a data cleaning INVESTIGATION agent. You do NOT execute any cleaning action.
        Required procedure:
        1. Always profile dataset first.
        2. Valid dataset columns: {valid_cols}. You MUST select 'column' strictly from this list. Do NOT invent non-existent column names (e.g. 'id').
        3. Look at the actions already covered in 'Already proposed actions' below — do NOT propose 
        an action for a target that already has one, unless explicitly asked to redo it.
        4. Pick exactly ONE remaining problem and propose a single CleaningAction for it.
        5. If every problematic issue already has a proposed action, or there are no more issues 
        to address, return a JSON object with "actionType": "none" to signal completion.
        
        IMPORTANT RULES FOR FINANCIAL DATA (Long-format):
        - For core accounting line items (revenue, assets, liabilities, equity, etc.), use IMPUTE_ZERO instead.
          Financial missing data usually means 'not reported' = 0.
        - Outlier detection MUST be calculated per 'line_item_canonical' (per-group), not globally across all values, 
        because different metrics (e.g. Total Assets vs Profit Margin) have completely different scales.
        - You should propose actions for specific line items, by specifying 'line_item_canonical' and 'statement_type' in your action output.
        - FIX_OCR_NUMERIC: Use for columns where numeric values were corrupted by OCR (spaces in numbers, O→0, l→1).
        - RECONCILE_IDENTITY: Use to flag rows where Assets != Liabilities + Equity. This only flags, does NOT auto-correct.
        - STANDARDIZE_UNIT: Use when values across periods have inconsistent currency units (e.g. VND vs million VND).
        
        Valid actionType values: "drop_rows", "impute_zero", 
        "cast_dtype", "drop_column", "fix_ocr_numeric", "reconcile_identity", "standardize_unit", "none"
        """
    )
    response = llm.invoke(
        [system_prompt] + 
        [HumanMessage(content=f"Dataset profile (pre-computed): {dataset_profile}\nValid dataset columns: {valid_cols}")] + 
        messages + [HumanMessage(content=
            f"""Already proposed actions (statement_type, period, column, line_item_canonical, actionType): {covered_actions}
            Summarize as raw JSON matching schema for ONE action only:
            Example JSON format:
            {{"file_path": "{file_path}", "file_format": "{file_format}", "reason": "clean data", "column": "value", "line_item_canonical": "tong_tai_san", "statement_type": "balance_sheet", "period": "2024Q4", "fiscal_year": 2024, "rows_affected": 0, "rows_ratio": 0.0, "risk_level": "low", "actionType": "none", "target_dtype": null, "target_unit": null}}
            """
        )]
    )
    res = parse_json_cleaning(getattr(response, "content", ""))
    if not res.file_path:
        res.file_path = file_path
    if not res.file_format:
        res.file_format = file_format

    all_actions = existing_actions + [res]
    summary = "\n".join(f"- {a.column} ({a.line_item_canonical}): {a.actionType}" for a in all_actions)
    if res.actionType == CleaningActionType.NONE:
        return Command(update={"cleaning_done": True})

    return Command(update={"pending_cleaning": all_actions, "messages": [HumanMessage(content=summary)]})

def route_tool_or_finish(state) -> Literal["cleaning_tools", "propose_action"]: 
    last_msg = state["messages"][-1]
    if getattr(last_msg, "tool_calls", None):
        return "cleaning_tools"
    return "propose_action"

def route_after_propose(state: AgentState) -> Literal["cleaning_agent", "__end__"]: 
    if state.get("cleaning_done") == True:
        return END
    return "cleaning_agent" 

cleaning_graph = StateGraph(AgentState)
cleaning_graph.add_node('cleaning_agent', data_cleaning_node)
cleaning_graph.add_node('cleaning_tools', tool_node)
cleaning_graph.add_node("propose_action", propose_action_node)

cleaning_graph.add_edge(START, "cleaning_agent")
cleaning_graph.add_conditional_edges(
    "cleaning_agent",
    route_tool_or_finish,
    {
        "cleaning_tools": "cleaning_tools", 
        "propose_action": "propose_action"
    }
)
cleaning_graph.add_conditional_edges(
    "propose_action",
    route_after_propose,
    {
        "cleaning_agent": "cleaning_agent",
        END: END,
    },
)
cleaning_graph.add_edge("cleaning_tools", "cleaning_agent")

cleaning = cleaning_graph.compile()