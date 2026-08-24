"""
year_worker subgraph — wraps the original single-year EDA pipeline
(supervisor → cleaning/eda/feature_engineering → validation → executor → review)
as a reusable subgraph that is invoked once per year/file via Send fan-out
from ``file_dispatcher`` in the top-level financial graph.

Per the design doc (section 3), ``generate_report`` and ``build_report`` are
**not** part of this subgraph — they live at the top-level graph after
``narrative_writer``.
"""

from langgraph.graph import StateGraph, START, END
from Class.AgentState import AgentState
from Subgraph.eda import eda
from Subgraph.cleaning import cleaning
from Subgraph.feature import feature_engineering
from Subgraph.validator import validation
from Subgraph.executor import executor_node, review_execution_node
from Subgraph.supervisor import (
    supervisor_node_subgraph,
    route_after_validation,
    route_after_review,
)

def build_year_worker_subgraph():
    """Compiles the single-year pipeline subgraph using existing nodes.
    
    Graph topology (matches section 3 ``per_year`` subgraph):
        supervisor → {cleaning | eda | feature_engineering}
                   → validation → executor → review
                   review -.retry.→ supervisor / validation / executor
    """
    graph = StateGraph(AgentState)
    
    graph.add_node('supervisor', supervisor_node_subgraph)
    graph.add_node('cleaning', cleaning)
    graph.add_node('eda', eda)
    graph.add_node('feature_engineering', feature_engineering)
    graph.add_node('validation', validation)
    graph.add_node('executor', executor_node)
    graph.add_node("review", review_execution_node)

    graph.add_edge(START, 'supervisor')

    # NOTE: The design doc (part 3) draws `supervisor` fanning out to the 3
    # sub-stages (`cleaning`, `eda`, `feature_engineering`). In LangGraph that
    # routing is implemented functionally by supervisor_node_subgraph via
    # `Command(goto=...)`, so no explicit plain edges are declared here —
    # LangGraph forbids multiple plain outgoing edges from a single node
    # (branches must use conditional edges or Command-based routing).

    graph.add_edge('cleaning', 'validation')
    graph.add_edge('eda', 'validation')
    graph.add_edge('feature_engineering', 'validation')

    graph.add_conditional_edges(
        "validation",
        route_after_validation,
        {
            "executor": "executor",
            "supervisor": "supervisor",
        }
    )
    
    graph.add_edge("executor", "review")
    
    graph.add_conditional_edges(
        "review",
        route_after_review,
        {
            "executor": "executor",
            "validation": "validation",
            "supervisor": "supervisor",
        }
    )

    return graph.compile()

# Build the compiled app instance for per-year execution
year_worker_app = build_year_worker_subgraph()

def year_worker_wrapper_node(state: dict) -> dict:
    """
    Adapter node that receives YearWorkerInput dict from Send,
    runs the inner single-year pipeline, and returns per_year_results entry.
    """
    file_path = state.get("file_path")
    year = state.get("year", 2024)
    
    initial_agent_state = {
        "file_path": file_path,
        "file_format": "csv",
        "check_start": True,
        "run_id": f"year_{year}",
        "messages": []
    }
    
    try:
        final_agent_state = year_worker_app.invoke(initial_agent_state)
        per_year_entry = {
            "year": year,
            "file_path": file_path,
            "dataset_profile": final_agent_state.get("dataset_profile", {}),
            "univariate": final_agent_state.get("univariate", []),
            "completed_actions": final_agent_state.get("completed_actions", []),
            "output_path": final_agent_state.get("output_path")
        }
    except Exception as e:
        # Fallback if execution fails on a single year file
        per_year_entry = {
            "year": year,
            "file_path": file_path,
            "error": str(e),
            "dataset_profile": {},
            "univariate": []
        }
        
    return {"per_year_results": [per_year_entry]}
