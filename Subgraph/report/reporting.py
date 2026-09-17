import os
from typing import Dict, List
from langgraph.types import interrupt

from Class.FinancialState import FinancialReportState
from Subgraph.ratio_trend import build_period_dataset, period_sort_key, select_period_data, select_scope
from Subgraph.report.slicer_compute import slice_dataset, slice_ratios, slice_trends, slice_flags, slice_reconciliation,slice_narratives, previous_period_key, next_period_key, period_deltas
from Subgraph.report.assemble import write_narrative_mda, assemble_report_markdown, assemble_rag_report_markdown, COMPARE_FIELDS

def generate_report_node(state: FinancialReportState) -> dict:
    metrics = state.get("period_metrics") or {}
    scope, fallback = select_scope(metrics)
    dataset = build_period_dataset(metrics) or fallback
    unit = state.get("currency_unit") or "VND_BILLION"
    chart_paths = list(state.get("chart_paths") or [])
    chart_map = state.get("chart_map") or {}
    symbol = state.get("symbol") or ""
    flags_all = list(state.get("validation_flags") or [])
    ratios_all = state.get("ratios") or {}
    trends_all = state.get("trends") or {}
    reconciliation_all = state.get("scope_reconciliation") or []
    narratives_all = state.get("narrative_store") or []

    if not dataset:
        report = assemble_report_markdown(
            "_Không có dữ liệu._", {}, {}, {}, [], chart_paths,
            symbol=symbol, scope=scope, unit=unit, chart_map=chart_map,
        )
        return {
            "narrative_mda": "",
            "narratives_mda": {},
            "final_report_md": report,
            "final_reports": {},
            "rag_report_md": report,
            "rag_reports": {},
        }

    feedback_context = state.get("feedback_context") or ""
    batch_id = str(state.get("batch_id") or "unknown")
    input_files = state.get("input_files") or []
    review_status = state.get("review_status") or "approved"
    retry_count = (state.get("retry_count") or 0) + 1

    reports: Dict[str, str] = {}
    rag_reports: Dict[str, str] = {}
    narratives: Dict[str, str] = {}

    sorted_keys = sorted(dataset.keys(), key=period_sort_key)
    for period_key in sorted_keys:
        period_scope = select_period_data(metrics, period_key)[0] or scope
        previous_key = previous_period_key(dataset, period_key)
        nxt_key = next_period_key(dataset, period_key)
        period_dataset = slice_dataset(dataset, period_key)
        period_ratios = slice_ratios(ratios_all, period_key)
        period_trends = slice_trends(trends_all, period_key)
        period_flags = slice_flags(flags_all, period_key)
        deltas = period_deltas(
            dataset.get(period_key) or {},
            (dataset.get(previous_key) or {}) if previous_key else {},
            COMPARE_FIELDS,
        )

        narrative = write_narrative_mda(
            period_dataset, period_ratios, period_trends, period_flags, symbol, period_scope,
            period_key=period_key, previous_period=previous_key,
            previous_data=dataset.get(previous_key) if previous_key else {}, deltas=deltas,
            feedback_context=feedback_context,
        )
        narratives[period_key] = narrative
        reports[period_key] = assemble_report_markdown(
            narrative, period_dataset, period_ratios, period_trends, period_flags,
            chart_paths, slice_reconciliation(reconciliation_all, period_key),
            slice_narratives(narratives_all, period_key),
            symbol=symbol, scope=period_scope, unit=unit, chart_map=chart_map,
            period_key=period_key, previous_period=previous_key,
        )
        rag_reports[period_key] = assemble_rag_report_markdown(
            narrative, period_dataset, period_ratios, period_trends, period_flags,
            chart_paths, slice_reconciliation(reconciliation_all, period_key),
            slice_narratives(narratives_all, period_key),
            symbol=symbol, scope=period_scope, unit=unit, chart_map=chart_map,
            period_key=period_key, previous_period=previous_key, next_period=nxt_key,
            batch_id=batch_id, input_files=input_files, review_status=review_status,
            report_version=retry_count,
        )

    first_key = sorted_keys[0] if sorted_keys else ""
    out_dir = os.path.join("example_output", batch_id)
    os.makedirs(out_dir, exist_ok=True)

    output_paths: List[str] = []
    rag_output_paths: List[str] = []
    if reports:
        for period_key in sorted_keys:
            period_dir = os.path.join(out_dir, str(period_key))
            os.makedirs(period_dir, exist_ok=True)

            reader_path = os.path.join(period_dir, f"Bao_Cao_Reader_{period_key}.md")
            with open(reader_path, "w", encoding="utf-8") as fh:
                fh.write(reports[period_key])
            output_paths.append(reader_path)

            default_path = os.path.join(period_dir, f"Bao_Cao_{period_key}.md")
            with open(default_path, "w", encoding="utf-8") as fh:
                fh.write(reports[period_key])

            rag_path = os.path.join(period_dir, f"Bao_Cao_RAG_{period_key}.md")
            with open(rag_path, "w", encoding="utf-8") as fh:
                fh.write(rag_reports[period_key])
            rag_output_paths.append(rag_path)

    elif "report" in locals() and report:
        output_path = os.path.join(out_dir, "Bao_Cao.md")
        with open(output_path, "w", encoding="utf-8") as fh:
            fh.write(report)
        output_paths.append(output_path)
        rag_output_paths.append(output_path)

    return {
        "narrative_mda": narratives.get(first_key, ""),
        "narratives_mda": narratives,
        "final_report_md": reports.get(first_key, report if "report" in locals() else ""),
        "final_reports": reports,
        "rag_report_md": rag_reports.get(first_key, report if "report" in locals() else ""),
        "rag_reports": rag_reports,
        "output_report_path": output_paths[0] if output_paths else None,
        "output_report_paths": output_paths,
        "rag_report_path": rag_output_paths[0] if rag_output_paths else None,
        "rag_report_paths": rag_output_paths,
    }

def build_report_node(state: FinancialReportState) -> dict:
    reports = state.get("final_reports") or {}
    rag_reports = state.get("rag_reports") or {}
    batch_id = str(state.get("batch_id") or "unknown")
    out_dir = os.path.join("example_output", batch_id)
    os.makedirs(out_dir, exist_ok=True)

    if not reports:
        reports = {batch_id: state.get("final_report_md", "")}

    output_paths: List[str] = []
    rag_output_paths: List[str] = []
    for period_key, report_md in sorted(reports.items(), key=lambda item: period_sort_key(item[0])):
        period_dir = os.path.join(out_dir, str(period_key))
        os.makedirs(period_dir, exist_ok=True)

        reader_path = os.path.join(period_dir, f"Bao_Cao_Reader_{period_key}.md")
        with open(reader_path, "w", encoding="utf-8") as fh:
            fh.write(report_md)
        output_paths.append(reader_path)

        default_path = os.path.join(period_dir, f"Bao_Cao_{period_key}.md")
        with open(default_path, "w", encoding="utf-8") as fh:
            fh.write(report_md)

        rag_md = rag_reports.get(period_key) or report_md
        rag_path = os.path.join(period_dir, f"Bao_Cao_RAG_{period_key}.md")
        with open(rag_path, "w", encoding="utf-8") as fh:
            fh.write(rag_md)
        rag_output_paths.append(rag_path)

    return {
        "output_report_path": output_paths[0] if output_paths else None,
        "output_report_paths": output_paths,
        "rag_report_path": rag_output_paths[0] if rag_output_paths else None,
        "rag_report_paths": rag_output_paths,
    }

def review_report_node(state: FinancialReportState) -> dict:
    reports = state.get("final_reports") or {}
    report_paths = list(state.get("output_report_paths") or [])
    if not report_paths and state.get("output_report_path"):
        report_paths = [state.get("output_report_path")]

    decision = interrupt({
        "type": "review_output",
        "message": "Duyệt báo cáo cuối? (approve/retry/abort)",
        "periods": sorted(reports.keys(), key=period_sort_key),
        "report_paths": report_paths,
        "flags": list(state.get("validation_flags") or [])[:10],
    })

    choice = "approve"
    rejection_reason = None
    if isinstance(decision, dict):
        value = decision.get("decision") or decision.get("choice") or decision.get("approved")
        if isinstance(value, bool):
            choice = "approve" if value else "abort"
        elif isinstance(value, str):
            choice = value.strip().lower()
        rejection_reason = decision.get("rejection_reason") or decision.get("reason") or decision.get("feedback")
    elif isinstance(decision, str):
        choice = decision.strip().lower()
        if ":" in decision:
            parts = decision.split(":", 1)
            choice = parts[0].strip().lower()
            rejection_reason = parts[1].strip()
    elif isinstance(decision, bool):
        choice = "approve" if decision else "abort"

    if choice in ("retry", "edit", "redo", "again"):
        choice = "retry"
    elif choice in ("abort", "reject", "no", "n", "cancel", "stop"):
        choice = "abort"
    else:
        choice = "approve"

    res = {"review_decision": choice, "review_status": choice}
    if choice == "retry":
        res["rejection_reason"] = rejection_reason or "Người dùng yêu cầu kiểm tra lại báo cáo."
    return res

def route_after_report_review(state: FinancialReportState) -> str:
    decision = str(state.get("review_decision") or "approve").lower()
    if decision == "retry":
        return "interpret_feedback"
    if decision == "abort":
        return "end"
    return "build_report"