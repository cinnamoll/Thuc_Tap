from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from typing import Literal, Annotated
from langchain_core.messages import SystemMessage, ToolMessage, HumanMessage
from langchain_deepseek import ChatDeepSeek
from langchain_core.tools import tool, InjectedToolCallId
from langgraph.prebuilt import ToolNode 
import polars as pl
from langgraph.types import Command
from Class.AgentState import AgentState
from Class.CleaningAction import CleaningAction, CleaningActionType
load_dotenv()

llm = ChatDeepSeek(model="deepseek-v4-flash")

@tool
def profile_dataset(file_path: str, file_format: str, tool_call_id: Annotated[str, InjectedToolCallId]) -> dict:
    """
    Scan a dataset (lazy, not loading the entire dataset into RAM) and return statistics:
    dtypes, number of nulls for both numerical and categorical columns and unique values for categorical column.
    Used to detect problems before suggesting cleaning.
    """
    if file_format == "csv":
        lf = pl.scan_csv(file_path)
    elif file_format == "parquet":
        lf = pl.scan_parquet(file_path)
    elif file_format == "json":
        lf = pl.scan_ndjson(file_path)
    else:
        raise ValueError(f"Don't support {file_format}")
    
    schema = lf.collect_schema()
    stats = lf.select([
        pl.all().null_count().name.suffix("_nulls"),
        pl.all().n_unique().name.suffix("_nunique"),
    ]).collect(engine='streaming')

    res = {
        "columns": list(schema.names()),
        "dtypes": {k: str(v) for k, v in schema.items()},
        "stats": stats.to_dicts()[0],
        "n_rows": lf.select(pl.len()).collect().item()
    }

    return Command(update={
        "dataset_profile": res,
        "messages": [ToolMessage(content=str(res), tool_call_id=tool_call_id)] 
    })

cleaning_tools = [profile_dataset]
tool_node = ToolNode(cleaning_tools)
cleaning_llm = llm.bind_tools(cleaning_tools)
cleaning_tools_dict = {cleaning_tool.name: cleaning_tool for cleaning_tool in cleaning_tools}

def data_cleaning_node(state:AgentState):
    response = cleaning_llm.invoke(state['messages'])
    return {'messages': [response]}    

def propose_action_node(state: AgentState) -> AgentState:
    messages = state['messages']
    existing_actions = state.get('pending_cleaning', [])
    covered_cols = [a.column for a in existing_actions]
    system_prompt = SystemMessage(
        content="""
        You are a data cleaning INVESTIGATION agent. You do NOT execute any cleaning action.
        Required procedure:
        1. Always call profile_dataset first to understand the dataset's problems.
        2. Look at the columns already covered in 'Already proposed actions' below — do NOT propose 
        an action for a column that already has one, unless explicitly asked to redo it.
        3. Pick exactly ONE remaining column with the most severe unresolved problem 
        (nulls, wrong dtype, etc.) and propose a single CleaningAction for it.
        4. If every problematic column already has a proposed action, or there are no more issues 
        to address, return a JSON object with "actionType": "NONE" to signal completion.
        """
    )
    structured_llm = llm.with_structured_output(CleaningAction, method='json_mode')
    res = structured_llm.invoke(
        [system_prompt] + 
        [HumanMessage(content=f"Dataset profile (pre-computed): {state['dataset_profile']}")] + 
        messages + [HumanMessage(content=
            f"""Already proposed actions (columns covered): {covered_cols}
            Summarize as JSON matching schema for ONE action only:
            {{"reason": str, "column": str, "rows_affected": int|null, "rows_ratio": float|null, 
            "risk_level": "low"|"medium"|"high"|null, "actionType": str, "target_dtype": str}}
            """
        )]
    )
    summary = "\n".join(f"- {a.column}: {a.actionType}" for a in existing_actions)
    if res.actionType == CleaningActionType.NONE:
        return Command(update={"cleaning_done": True})

    return Command(update={
        "pending_cleaning": existing_actions + [res],
        "messages": [HumanMessage(content=summary)]
    })

def route_tool_or_finish(state) -> Literal["cleaning_tools", "propose_action"]: 
    last_msg = state["messages"][-1]
    if getattr(last_msg, "tool_calls", None):
        return "cleaning_tools"
    return "propose_action"

def route_after_propose(state: AgentState) -> Literal["cleaning_agent", END]: #type:ignore
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

# img = cleaning.get_graph().draw_mermaid_png()
# with open('Subgraph_Img/cleaning_image.png', 'wb') as f:
#     f.write(img)