from dotenv import load_dotenv
import os
from langgraph.graph import StateGraph, START, END
from typing import Annotated, Sequence, List, Optional, TypedDict
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, ToolMessage
from operator import add as add_messages
from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace, HuggingFaceEmbeddings
# from langchain_community.document_loaders import PyPDFLoader
from langchain_chroma import Chroma
from langchain_core.tools import tool, StructuredTool
from langgraph.prebuilt import ToolNode, tools_condition
from pydantic import BaseModel, FilePath
import pandas as pd
import polars
from IPython.display import Image, display
from dotenv import load_dotenv

load_dotenv()

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    cols: Optional[List[str]]
    metadata: Optional[List[str]]
    
# class MetaData(BaseModel):
#     col_name: str
#     col_desc: str
    
@tool
def extract_columns(file_path:str) -> str:
    """
    This tool reads and extracts column name and description from the file
    Args:
        file_path (str): metadata file path 
    
    Return:
        Metadata object contains column name and brief column description
    """
    if not os.path.exists(file_path):
        return []
    
    _, file_extension = os.path.splitext(file_path)
    
    cols = []
    
    try:
        if file_extension == '.csv':
            df = polars.read_csv(file_path, n_rows=0)
            cols = df.columns
        elif file_extension in ['.xlsx', '.xls']:
            df = polars.read_excel(file_path, n_rows=0)
            cols = df.columns
        elif file_extension == '.json':
            df = polars.read_json(file_path)
            cols = df.columns
    except Exception as e:
        return str(e)

    return cols

hf_endpoint = HuggingFaceEndpoint(
    repo_id='Qwen/Qwen2.5-7B-Instruct',
)

llm = ChatHuggingFace(llm=hf_endpoint).bind_tools(tools=[extract_columns])

    
def extract_metadata_node(state: AgentState):
    """
    This node invokes the LLM. If the user asks about a dataset, 
    the LLM will generate a tool_call to 'extract_columns'.
    """
    messages = state['messages']
    
    system_prompt = SystemMessage(
        content="You are a data assistant. NEVER call extract_columns with a placeholder "
                "or example file path. If the user has not provided a real, specific file "
                "path (e.g. 'data.csv', './sales/report.xlsx'), ask them for it instead of "
                "guessing or calling the tool. After receiving tool results, only describe "
                "columns that actually appear in the tool output — never invent columns "
                "that were not returned."
    )
    
    response = llm.invoke([system_prompt] + messages)
    return {'messages': [response]}

graph = StateGraph(AgentState)
graph.add_node('extract_metadata', extract_metadata_node)
graph.add_node('tools', ToolNode(tools=[extract_columns]))

graph.add_edge(START, 'extract_metadata')
graph.add_conditional_edges(
    'extract_metadata',
    tools_condition
)
graph.add_edge('tools', 'extract_metadata')

app = graph.compile()

user_input = input("Enter: ")
while user_input.lower() != 'exit':
    for event in app.stream({'messages': [HumanMessage(content=user_input)]}):
        for node_name, node_state in event.items():
            print(f"\n--- Output from {node_name} ---")
            last_message = node_state['messages'][-1]
            print(last_message.content if last_message.content else "[Tool Call]")
            
    user_input = input("Enter: ")
    
# @tool
# def clean_dataset(file_path:FilePath):
#     pass

# def condition_edge(state:AgentState) -> AgentState:
#     messages = state['messages']