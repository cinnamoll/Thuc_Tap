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
import uuid
from datetime import datetime

from Class.AgentState import AgentState
from Subgraph.eda import eda
from Subgraph.cleaning import cleaning
from Subgraph.feature import feature_engineering
from Subgraph.validator import validation
from Subgraph.executor import executor_node, review_execution_node
from Subgraph.report import generate_report_node, build_report_file_node

load_dotenv()

hf_endpoint = HuggingFaceEndpoint(
    repo_id='Qwen/Qwen2.5-7B-Instruct',
)

llm = ChatHuggingFace(llm=hf_endpoint) 

def generate_id_node(state:AgentState):
    run_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    return {"run_id":run_id}

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

def supervisor_node(state: AgentState) -> Command[Literal["cleaning", "eda", "feature_engineering", "review", "generate_report", END]]: #type:ignore
    llm_router = llm.with_structured_output(RouteDecision)

    messages = [
        SystemMessage(content=SUPERVISOR_PROMPT),
        HumanMessage(content=(
            f"Metadata dataset:\n{state.get('metadata')}\n"
            f"Completed steps: {state.get('completed_steps', [])}\n" #####
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
    
def route_after_review(state:AgentState) -> Literal["executor", "validation", "supervisor"]:
    if state["review_decision"] != "retry":
        return "supervisor"
    if state.get("retry_count", 0) >= 3:
        return "supervisor"         
    if state.get("current_action") != state.get("pending_action"):
        return "validation"         
    return "executor"   

graph = StateGraph(AgentState)

graph.add_node('generate_id', generate_id_node)
graph.add_node('supervisor', supervisor_node)
graph.add_node('cleaning', cleaning)
graph.add_node('eda', eda)
graph.add_node('feature_engineering', feature_engineering)
graph.add_node('validation', validation)
graph.add_node('executor', executor_node)
graph.add_node("review", review_execution_node)
graph.add_node('generate_report', generate_report_node)
graph.add_node('build_report', build_report_file_node)

graph.add_edge(START, 'generate_id')
graph.add_edge('generate_id', 'supervisor')
graph.add_edge('supervisor', 'cleaning')
graph.add_edge('supervisor', 'eda')
graph.add_edge('supervisor', 'feature_engineering')
graph.add_edge('cleaning', 'validation')
graph.add_edge('eda', 'validation')
graph.add_edge('feature_engineering', 'validation')
graph.add_edge('validation', "executor")
graph.add_edge("executor", "review")
graph.add_edge("review", "generate_report")
graph.add_edge("generate_report", "build_report")
graph.add_edge("build_report", END)

# graph.add_conditional_edges(
    
# )

graph.add_conditional_edges(
    "review",
    route_after_review,
    {
        "executor": "executor",
        "validation": "validation",
        "supervisor": "supervisor",
    },
)

app = graph.compile()

img = app.get_graph().draw_mermaid_png()
with open('graph_image.png', 'wb') as f:
    f.write(img)

# user_input = input("Enter: ")
# while user_input.lower() != 'exit':
#     for event in app.stream({'messages': [HumanMessage(content=user_input)]}):
#         for node_name, node_state in event.items():
#             print(f"\n--- Output from {node_name} ---")
#             last_message = node_state['messages'][-1]
#             print(last_message.content if last_message.content else "[Tool Call]")
            
#     user_input = input("Enter: ")