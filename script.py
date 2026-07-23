from dotenv import load_dotenv
import os
from langgraph.graph import StateGraph, START, END
from typing import List, TypedDict, Literal
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode, tools_condition
import polars as pl
from langgraph.types import interrupt, Command

from BT_Thuc_Tap.Class.AgentState import AgentState
from BT_Thuc_Tap.Subgraph.eda import eda
from BT_Thuc_Tap.Subgraph.cleaning import cleaning
from BT_Thuc_Tap.Subgraph.feature import feature_engineering

load_dotenv()

hf_endpoint = HuggingFaceEndpoint(
    repo_id='Qwen/Qwen2.5-7B-Instruct',
)

llm = ChatHuggingFace(llm=hf_endpoint) 

def scan_file(file_path:str, file_format: str):
    if file_format == 'csv':
        df = pl.read_csv(file_path)
    elif file_format in ['xlsx', 'xls']:
        df = pl.read_excel(file_path)
    elif file_format == 'json':
        df = pl.read_json(file_path)
    return df

@tool
def extract_columns(file_path: str, file_format: str) -> List[str]:
    """
    This tool reads and extracts column name from the file
    Args:
        file_path (str): metadata file path 
    
    Return:
        List of column names
    """
    if not os.path.exists('file_path'):
        return []    
    cols = []
    df = scan_file('file_path', 'file_format')
    cols = df.columns
    return cols

def extract_metadata_node(state: AgentState):
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


#main graph
tools = [extract_columns]  

llm = llm.bind_tools(tools=tools) 

graph = StateGraph(AgentState)
graph.add_node('extract_metadata', extract_metadata_node)
graph.add_node('tools', ToolNode(tools=tools))

graph.add_edge(START, 'extract_metadata')
graph.add_conditional_edges(
    'extract_metadata',
    tools_condition
)
graph.add_edge('tools', 'extract_metadata')

class RouteDecision(TypedDict):
    next: Literal["cleaning", "eda", "feature_engineering", "FINISH"]
    reason: str 

SUPERVISOR_PROMPT = """
    You are the Supervisor coordinating a data analysis pipeline with the following workers:
    - Cleaning: Handles binning, encoding processing, and general data cleaning.
    - EDA: Handles Univariate Analysis, Multivariate Analysis, and Charting.
    - feature_engineering: Handles feature transformation, creation, and selection.

    Your primary directive is to respect the user's explicit intent:

    1. Check User Intent First: 
    - If the user's latest request was only to "extract metadata" (or inspect the dataset) 
    and they did NOT explicitly ask to clean, analyze, or engineer features yet, return "FINISH" immediately. 
    Do not trigger any workers.
    - Only delegate to a worker if the user has explicitly requested a task that falls under their description.

    2. Wait for Confirmation:
    - Stop and return "FINISH" after a worker completes its task to allow the user to review the output and give confirmation.

    3. Avoid Repetition:
    - Do not repeat a step that is already in the completed steps list unless the user explicitly asks to run it again.

    If no further actions are requested or required by the user's prompt, return "FINISH".
"""

def supervisor_node(state: AgentState) -> Command[Literal["cleaning", "eda", "feature_engineering", END]]: #type:ignore
    llm_router = llm.with_structured_output(RouteDecision)

    messages = [
        SystemMessage(content=SUPERVISOR_PROMPT),
        HumanMessage(content=(
            f"Metadata dataset:\n{state.get('metadata')}\n"
            f"Completed steps: {state.get('completed_steps', [])}\n"
            "Proceed to next step"
        ))
    ]
    
    decision = llm_router.invoke(messages)
    goto = decision["next"]
    
    if goto == "FINISH":
        goto = END

    return Command(
        goto=goto,
        update={
            "next_step": decision['next'],
            "messages": [HumanMessage(content=f"[Supervisor] -> { decision['next']}: { decision['reason']}")],
        },
    )

graph.add_node('supervisor', supervisor_node)
graph.add_edge('extract_metadata', 'supervisor')

graph.add_node('cleaning', cleaning)
graph.add_edge('cleaning', 'supervisor')

graph.add_node('eda', eda)
graph.add_edge('eda', 'supervisor')

graph.add_node('feature_engineering', feature_engineering)
graph.add_edge('feature_engineering', 'supervisor')

app = graph.compile()

img = app.get_graph().draw_mermaid_png()
with open('graph_image.png', 'wb') as f:
    f.write(img)

user_input = input("Enter: ")
while user_input.lower() != 'exit':
    for event in app.stream({'messages': [HumanMessage(content=user_input)]}):
        for node_name, node_state in event.items():
            print(f"\n--- Output from {node_name} ---")
            last_message = node_state['messages'][-1]
            print(last_message.content if last_message.content else "[Tool Call]")
            
    user_input = input("Enter: ")