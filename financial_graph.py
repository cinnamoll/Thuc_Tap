from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
import uuid
from datetime import datetime

from Class.FinancialState import FinancialReportState
from Subgraph.year_worker import year_worker_wrapper_node
from Subgraph.multi_year.dispatcher import file_dispatcher, route_to_year_workers, result_reducer
from Subgraph.multi_year.normalizer import schema_mapper, unit_currency_normalizer
from Subgraph.multi_year.accounting import accounting_identity_checker, yoy_variance_flagger
from Subgraph.multi_year.analysis import ratio_engine, trend_engine
from Subgraph.multi_year.reporting import (
    chart_composer, narrative_writer, generate_financial_report, build_financial_report
)

load_dotenv()

def generate_id_node(state: FinancialReportState) -> dict:
    return {"run_id": f"fin_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"}

def build_financial_graph():
    workflow = StateGraph(FinancialReportState)
    
    # Register Nodes
    workflow.add_node("generate_id", generate_id_node)
    workflow.add_node("file_dispatcher", file_dispatcher)  # Module 1 (node)
    workflow.add_node("year_worker", year_worker_wrapper_node)
    workflow.add_node("result_reducer", result_reducer)
    
    # Module 2
    workflow.add_node("schema_mapper", schema_mapper)
    workflow.add_node("unit_currency_normalizer", unit_currency_normalizer)
    
    # Module 3
    workflow.add_node("accounting_identity_checker", accounting_identity_checker)
    workflow.add_node("yoy_variance_flagger", yoy_variance_flagger)
    
    # Module 4
    workflow.add_node("ratio_engine", ratio_engine)
    workflow.add_node("trend_engine", trend_engine)
    
    # Module 5
    workflow.add_node("chart_composer", chart_composer)
    workflow.add_node("narrative_writer", narrative_writer)
    # Final report stage — node names kept identical to the design doc (part 3)
    # (`generate_report` -> `build_report`), implemented by the new multi-year nodes.
    workflow.add_node("generate_report", generate_financial_report)
    workflow.add_node("build_report", build_financial_report)

    # Edges & Routing
    workflow.add_edge(START, "generate_id")
    workflow.add_edge("generate_id", "file_dispatcher")

    # Fan-Out: `file_dispatcher -->|Send x N| per_year` (module 1)
    workflow.add_conditional_edges(
        "file_dispatcher",
        route_to_year_workers,
        ["year_worker"]
    )
    
    # Fan-In from year_worker to result_reducer
    workflow.add_edge("year_worker", "result_reducer")
    
    # Sequential Multi-Year Processing Steps
    workflow.add_edge("result_reducer", "schema_mapper")
    workflow.add_edge("schema_mapper", "unit_currency_normalizer")
    workflow.add_edge("unit_currency_normalizer", "accounting_identity_checker")
    workflow.add_edge("accounting_identity_checker", "yoy_variance_flagger")
    workflow.add_edge("yoy_variance_flagger", "ratio_engine")
    workflow.add_edge("ratio_engine", "trend_engine")
    workflow.add_edge("trend_engine", "chart_composer")
    workflow.add_edge("chart_composer", "narrative_writer")
    workflow.add_edge("narrative_writer", "generate_report")
    workflow.add_edge("generate_report", "build_report")
    workflow.add_edge("build_report", END)

    checkpointer = InMemorySaver()
    return workflow.compile(checkpointer=checkpointer)

financial_app = build_financial_graph()

if __name__ == "__main__":
    print("Multi-Year Financial Graph successfully compiled!")
    print(f"Graph nodes: {list(financial_app.get_graph().nodes.keys())}")
