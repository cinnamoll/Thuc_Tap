from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from typing import Literal, Annotated
from langchain_core.messages import SystemMessage, ToolMessage, HumanMessage
from langchain_deepseek import ChatDeepSeek
from langgraph.prebuilt import ToolNode
from langchain_core.tools import tool, InjectedToolCallId
import polars as pl
from langgraph.types import Command

from Class.AgentState import AgentState
from Class.EngineeringAction import EngineeringAction, EncodingType, BinningType

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
    
    lf = get_lf(file_path, file_format)
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
    else: 
        return "Unsupported encode type"   
    
    res = {
        "Target Column": column,
        "Method": encode,
        f"First {length} rows": encoded_df
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
    
    lf = get_lf(file_path, file_format)
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
            new_df = df.with_columns(((pl.col(column) - mean) / std).alias(f"{column}_std"))
        else:
            return "Std is None. No binning with this column"
    elif encode == 'equal_width':
        min_val = df.select(pl.col(column).min()).item()
        max_val = df.select(pl.col(column).max()).item()
        
        step = (max_val - min_val) / n_bin
        breaks = [min_val + i * step for i in range(1, n_bin)]
        
        new_df = df.with_columns(pl.col(column).cut(breaks).alias(f"{column}_binned"))
    elif encode == 'quantile':
        new_df = df.with_columns(
                pl.col(column)
                .qcut(n_bin, allow_duplicates=True)
                .alias(f"{column}_binned")
            )
    else: 
        return "Unsupported binning type" 
    
    res = {
        "Target Column": column,
        "Method": encode,
        f"First {length} rows": new_df
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
    covered_cols = [[a.column, a.actionType] for a in existing_actions]
    system_prompt = SystemMessage(
    content="""
        You are a data feature engineering INVESTIGATION agent. You do NOT execute any transformation 
        action.
        Required procedure:
        1. Call the encoding tool for categorical columns and preview the column(s) head after encoding; 
        call the standardization or binning tool for numerical columns and preview the column(s) head 
        after transformation.
        2. Look at the actions already covered in 'Already proposed actions' below — do NOT propose 
        an action for a (column, actionType) pair that already has one, unless explicitly asked to redo it.
        3. Pick exactly ONE remaining column/transformation with the most impactful unresolved issue 
        and propose a single EngineeringAction for it.
        4. If every column has already been adequately transformed, or there is nothing further worth 
        proposing, return a JSON object with "actionType": "NONE" to signal completion.
        """
    )
    structured_llm = llm.with_structured_output(EngineeringAction, method='json_mode')
    res = structured_llm.invoke(
        [system_prompt] + messages + [HumanMessage(content=
            f"""Already proposed actions (column, actionType): {covered_cols}
            Summarize as JSON matching schema for ONE action only:
            {{"reason": str, "column": str, "rows_affected": int | null, "rows_ratio": float | null,
                "risk_level": "low" | "medium" | "high" | null, "actionType": str, "n_bin": int}}\n
            Preview the column for user using {state['preview_feature']}
            """
        )]
    )

    summary = "\n".join(f"- {a.column}: {a.actionType}" for a in existing_actions)
    if res.actionType in (EncodingType.NONE, BinningType.NONE): 
        return Command(update={"engineer_done": True})

    return Command(update={
        "pending_engineering": existing_actions + [res],
        "messages": [HumanMessage(content=summary)]
    })

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