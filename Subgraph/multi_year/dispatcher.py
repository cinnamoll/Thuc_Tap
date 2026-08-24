import os
import re
from langgraph.types import Send
from Class.FinancialState import FinancialReportState

def file_dispatcher(state: FinancialReportState) -> dict:
    """
    Module 1 — node: reads the input file list, extracts the fiscal year from each
    file name (or falls back to a positional offset), and stores one fan-out task
    per (year, file) into state. The actual Send fan-out happens in the
    `route_to_year_workers` conditional edge (kept as separate steps so the graph
    has a real `file_dispatcher` node as depicted in the design doc, part 3).
    """
    input_files = state.get("input_files", [])
    tasks = []

    for idx, path in enumerate(input_files):
        filename = os.path.basename(path)
        year_match = re.search(r'(20\d{2}|19\d{2})', filename)
        if year_match:
            year = int(year_match.group(1))
        else:
            # Default fallback if year not in filename
            year = 2020 + idx

        tasks.append({
            "file_path": path,
            "year": year,
            "company_code": state.get("company_name"),
        })

    return {"dispatched_tasks": tasks}

def route_to_year_workers(state: FinancialReportState) -> list[Send]:
    """
    Module 1 — conditional edge: fans out one `year_worker` invocation per task.
    This is the LangGraph equivalent of `file_dispatcher -->|Send x N| per_year`
    in the design doc (part 3).
    """
    return [
        Send("year_worker", task)
        for task in state.get("dispatched_tasks", [])
    ]

def result_reducer(state: FinancialReportState) -> dict:
    """
    Fan-in node: Sorts per_year_results by fiscal year and constructs long_format_dataset.
    """
    raw_results = state.get("per_year_results", [])
    sorted_results = sorted(raw_results, key=lambda x: x.get("year", 0))
    
    long_format = {res["year"]: res.get("dataset_profile", {}) for res in sorted_results if "year" in res}
    
    return {
        "long_format_dataset": long_format
    }
