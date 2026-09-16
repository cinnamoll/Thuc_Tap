import os
import json
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_deepseek import ChatDeepSeek
from langgraph.types import interrupt

from Class.FinancialState import FinancialReportState
from Subgraph.charts import SUBSECTION_TITLES, to_billion
from Subgraph.ratio_trend import build_period_dataset, period_sort_key, select_period_data, select_scope

load_dotenv()
llm = ChatDeepSeek(model="deepseek-v4-flash")

TABLE_FIELDS: List[tuple] = [
    ("tong_tai_san", "Tổng tài sản"),
    ("tai_san_ngan_han", "Tài sản ngắn hạn"),
    ("tai_san_dai_han", "Tài sản dài hạn"),
    ("no_phai_tra", "Nợ phải trả"),
    ("von_chu_so_huu", "Vốn chủ sở hữu"),
    ("tong_nguon_von", "Tổng nguồn vốn"),
    ("doanh_thu", "Doanh thu"),
    ("gia_von_hang_ban", "Giá vốn hàng bán"),
    ("loi_nhuan_gop", "Lợi nhuận gộp"),
    ("loi_nhuan_truoc_thue", "Lợi nhuận trước thuế"),
    ("loi_nhuan_sau_thue", "Lợi nhuận sau thuế"),
    ("luu_chuyen_kinh_doanh", "Lưu chuyển tiền HĐKD"),
    ("luu_chuyen_trong_ky", "Lưu chuyển tiền thuần"),
    ("tien_cuoi_ky", "Tiền cuối kỳ"),
]

def render_statement_tables(dataset: Dict[str, Dict[str, float]], unit: str = "VND_BILLION") -> str:
    keys = sorted((dataset or {}).keys(), key=period_sort_key)
    if not keys:
        return "_Không có dữ liệu kỳ nào._"
    lines = ["| Chỉ tiêu | " + " | ".join(keys) + " |", "|---" * (len(keys) + 1) + "|"]
    for field, label in TABLE_FIELDS:
        values = [(dataset.get(key) or {}).get(field) for key in keys]
        if all(v is None for v in values):
            continue
        cells = " | ".join("-" if v is None else f"{to_billion(v, unit):,.1f}" for v in values)
        lines.append(f"| {label} | {cells} |")
    return "\n".join(lines)

def render_chart_section(chart_map: Dict[str, List[str]], chart_paths: List[str] = None, subsection_titles: Dict[str, str] = None) -> List[str]:
    titles = subsection_titles or SUBSECTION_TITLES

    def subsection_sort_key(section: Any) -> tuple:
        try:
            return tuple(int(part) for part in str(section).split("."))
        except ValueError:
            return (99, 99)

    pairs = [
        (section, path, titles.get(section) or f"Mục {section}")
        for section in sorted((chart_map or {}).keys(), key=subsection_sort_key)
        for path in (chart_map.get(section) or [])
        if path
    ]
    if not pairs:
        return ["\n## 6. Biểu đồ\n", "_Không có biểu đồ._"]

    charts_root = os.path.dirname(os.path.dirname(pairs[0][1]))
    lines: List[str] = ["\n## 6. Biểu đồ\n"]
    lines.append(f"_Biểu đồ các chỉ số mục 1.1–1.5 (vẽ trên toàn bộ khoảng thời gian) được lưu tại `{charts_root}/`:_\n")
    lines.extend(f"- Mục {section} — {label}: `{path}`" for section, path, label in pairs)
    return lines

def write_narrative_mda(dataset: Dict[str, Dict[str, float]], ratios: dict, trends: dict, flags: list, symbol: str = "", scope: str = "", period_key: str = "", previous_period: str = "", previous_data: dict = None, deltas: dict = None) -> str:
    prompt = f"""
    Viết báo cáo phân tích quản trị (MD&A) bằng tiếng Việt CHO MỘT KỲ dựa trên dữ liệu sau.
    - Doanh nghiệp: {symbol or 'N/A'} - phạm vi báo cáo: {scope or 'N/A'}
    - Kỳ báo cáo: {period_key or 'N/A'}
    - Số liệu tài chính của kỳ này (đơn vị: tỷ VND): {dataset}
    - Chỉ số của kỳ này (ROE, ROA, Debt/Equity, Net Margin): {ratios}
    - Kỳ trước: {previous_period or 'không có'}
    - Số liệu kỳ trước: {previous_data if previous_data else 'không có'}
    - Mức thay đổi so với kỳ trước: {deltas if deltas else 'không có'}
    - Tăng trưởng của kỳ này (QoQ/YoY/CAGR): {trends}
    - Cảnh báo & bất thường: {flags}

    Yêu cầu: (1) CHỈ phân tích số liệu của KỲ báo cáo ở trên; (2) với mỗi chỉ tiêu trọng yếu,
    chú thích rõ chỉ tiêu đó đã thay đổi như thế nào so với kỳ trước (nếu có dữ liệu kỳ trước)
    và nêu nguyên nhân/cảnh báo kế toán liên quan; (3) khuyến nghị ngắn gọn.
    """
    res = llm.invoke([
        SystemMessage(content="Bạn là Chuyên gia Phân tích Tài chính Cao cấp."),
        HumanMessage(content=prompt),
    ])
    content = getattr(res, "content", None)
    if content:
        return content
    return f"_Không có nội dung MD&A. Chỉ số: {ratios}_"

def assemble_report_markdown(narrative: str, dataset: Dict[str, Dict[str, float]], ratios: dict,
                             trends: dict, flags: list, chart_paths: List[str],
                             scope_reconciliation: List[Dict[str, Any]] | None = None,
                             narrative_store_path: Optional[str] = None,
                             symbol: str = "", scope: str = "", unit: str = "VND_BILLION",
                             chart_map: Dict[str, List[str]] | None = None,
                             period_key: str = "", previous_period: str = "",
                             health_score: Dict[str, Any] | None = None,
                             forecasts: Dict[str, Any] | None = None,
                             prediction_intervals: Dict[str, Any] | None = None,
                             scenarios: Dict[str, Any] | None = None) -> str:
    # Load narrative store from file path if provided
    narrative_store = []
    if narrative_store_path and os.path.exists(narrative_store_path):
        try:
            with open(narrative_store_path, 'r') as f:
                narrative_store = json.load(f)
        except Exception:
            narrative_store = []
    keys = sorted((dataset or {}).keys(), key=period_sort_key)
    report = [f"# BÁO CÁO PHÂN TÍCH TÀI CHÍNH — {symbol or 'DOANH NGHIỆP'}"]
    if period_key:
        compare = f" · **So sánh với:** {previous_period}" if previous_period else ""
        report.append(f"**Phạm vi dữ liệu:** {scope or 'n/a'} · **Kỳ:** {period_key}{compare} · Đơn vị: tỷ VND\n")
    else:
        report.append(f"**Phạm vi dữ liệu:** {scope or 'n/a'} · **Số kỳ:** {len(keys)} ({keys[0] if keys else 'n/a'} → {keys[-1] if keys else 'n/a'}) · Đơn vị: tỷ VND\n")

    if health_score:
        tot = health_score.get("total_score", 0.0)
        cat = health_score.get("risk_category", "N/A")
        comp = health_score.get("components") or {}
        report.append("### Thẻ điểm Sức khỏe Tài chính (Health Dashboard)")
        report.append(f"- **Điểm tổng hợp:** `{tot}/100` · **Xếp hạng:** **{cat}**")
        report.append(f"- **Chi tiết:** Sinh lời (`{comp.get('profitability',0)}/35`), Đòn bẩy (`{comp.get('leverage',0)}/25`), Thanh khoản (`{comp.get('liquidity',0)}/25`), Dòng tiền (`{comp.get('cash_flow',0)}/15`)\n")

    report.append("## 1. Phân tích Tường thuật Quản trị (MD&A)\n")
    report.append(narrative or "_Không có nội dung._")

    report.append("\n## 2. Bảng chỉ tiêu chính theo kỳ\n")
    report.append(render_statement_tables(dataset, unit))

    report.append("\n## 3. Chỉ số tài chính\n")
    report.append("| Chỉ số | " + " | ".join(keys) + " |")
    report.append("|---" * (len(keys) + 1) + "|")
    for name, series in (ratios or {}).items():
        cells = " | ".join(f"{(series.get(k) if series.get(k) is not None else 0):,.2f}" for k in keys)
        report.append(f"| {name} | {cells} |")

    report.append("\n## 4. Tăng trưởng (QoQ / YoY / CAGR)\n")
    report.append("```json")
    report.append(f"{trends}")
    report.append("```")

    if forecasts:
        report.append("\n## 4.1. Dự báo Tài chính & Khoảng tin cậy (Forecasts & Prediction Intervals)\n")
        report.append("| Chỉ tiêu | Dự báo Trend | Khoảng tin cậy 95% [Dưới, Trên] | San bằng mũ (SES) | Tăng trưởng kép (CAGR) |")
        report.append("|---|---|---|---|---|")
        for field, fc in forecasts.items():
            pi = (prediction_intervals or {}).get(field) or {}
            low = pi.get("lower_bound", 0.0)
            up = pi.get("upper_bound", 0.0)
            report.append(
                f"| {field} | {fc.get('linear_trend', 0.0):,.1f} | [{low:,.1f}, {up:,.1f}] | "
                f"{fc.get('exponential_smoothing', 0.0):,.1f} | {fc.get('compound_growth', 0.0):,.1f} |"
            )

    if scenarios and scenarios.get("stress_tests"):
        report.append("\n## 4.2. Phân tích Kịch bản & Thử nghiệm Ứng suất (Stress Testing)\n")
        report.append("| Kịch bản | Biến đổi đầu vào | Doanh thu simulated | LNST simulated | Lệch LNST |")
        report.append("|---|---|---|---|---|")
        for sc_name, sc_info in scenarios["stress_tests"].items():
            sim_out = sc_info.get("simulated_outputs") or {}
            deltas = sc_info.get("deltas_from_base") or {}
            report.append(
                f"| {sc_name} | {sc_info.get('modifications')} | {sim_out.get('doanh_thu', 0.0):,.1f} | "
                f"{sim_out.get('loi_nhuan_sau_thue', 0.0):,.1f} | {deltas.get('loi_nhuan_sau_thue', 0.0):,.1f} |"
            )

    report.append("\n## 5. Cảnh báo Kế toán & Bất thường\n")
    if flags:
        for flag in flags:
            period = flag.get("period_key") or flag.get("year") or ""
            report.append(f"- **[{flag.get('severity', 'N/A')}]** {period} — {flag.get('message', '')}")
    else:
        report.append("Không ghi nhận bất thường kế toán hoặc vi phạm đẳng thức.")

    report.extend(render_chart_section(chart_map, chart_paths))

    report.append("\n## Phụ lục A — Đối chiếu Riêng vs Hợp nhất\n")
    reconciliations = scope_reconciliation or []
    if reconciliations:
        report.append("| Kỳ | Chỉ tiêu | Hợp nhất | Riêng | Lệch | Mức |")
        report.append("|---|---|---|---|---|---|")
        for rec in reconciliations:
            report.append(
                f"| {rec.get('period_key')} | {rec.get('field')} | {rec.get('consolidated'):,.0f} | "
                f"{rec.get('separate'):,.0f} | {rec.get('delta'):,.0f} | {rec.get('severity')} |"
            )
    else:
        report.append("_Không đủ dữ liệu để đối chiếu (cần cả bản riêng và hợp nhất).")

    report.append("\n## Phụ lục B — Thuyết minh trọng yếu\n")
    narratives = narrative_store or []
    if narratives:
        for item in narratives[:15]:
            title = item.get("note_title") or item.get("note_id") or ""
            text = (item.get("text") or "").strip().replace("\n", " ")
            report.append(f"- **{title}** ({item.get('period_key', '')}): {text[:300]}")
    else:
        report.append("_Không có đoạn thuyết minh nào được trích._")
    return "\n".join(report)

def slice_dataset(dataset: Dict[str, Dict[str, float]], period_key: str) -> Dict[str, Dict[str, float]]:
    data = (dataset or {}).get(period_key)
    return {period_key: data} if data is not None else {}

def slice_ratios(ratios: Dict[str, Dict[str, float]], period_key: str) -> Dict[str, Dict[str, float]]:
    out: Dict[str, Dict[str, float]] = {}
    for name, series in (ratios or {}).items():
        if isinstance(series, dict) and series.get(period_key) is not None:
            out[name] = {period_key: series.get(period_key)}
    return out

def slice_trends(trends: Dict[str, Dict[str, float]], period_key: str) -> Dict[str, Dict[str, float]]:
    out: Dict[str, Dict[str, float]] = {}
    for field, entry in (trends or {}).items():
        kept = {
            key: value for key, value in (entry or {}).items()
            if key == "CAGR_%" or key.endswith(f"_{period_key}_%")
        }
        if kept:
            out[field] = kept
    return out

def slice_flags(flags: List[Dict[str, Any]], period_key: str) -> List[Dict[str, Any]]:
    return [f for f in (flags or []) if not f.get("period_key") or str(f.get("period_key")) == str(period_key)]

def slice_reconciliation(reconciliation: List[Dict[str, Any]], period_key: str) -> List[Dict[str, Any]]:
    return [r for r in (reconciliation or []) if str(r.get("period_key")) == str(period_key)]

def slice_narratives(narrative_store: List[Dict[str, Any]], period_key: str) -> List[Dict[str, Any]]:
    return [n for n in (narrative_store or []) if str(n.get("period_key")) == str(period_key)]

def previous_period_key(dataset: Dict[str, Dict[str, float]], period_key: str) -> str:
    keys = sorted((dataset or {}).keys(), key=period_sort_key)
    if period_key not in keys:
        return ""
    index = keys.index(period_key)
    return keys[index - 1] if index > 0 else ""

def period_deltas(current: Dict[str, float], previous: Dict[str, float], fields: List[str]) -> Dict[str, Dict[str, float]]:
    deltas: Dict[str, Dict[str, float]] = {}
    for field in fields:
        cur = (current or {}).get(field)
        prev = (previous or {}).get(field)
        if cur is None or prev is None:
            continue
        deltas[field] = {
            "ky_nay": round(float(cur), 2),
            "ky_truoc": round(float(prev), 2),
            "thay_doi": round(float(cur) - float(prev), 2),
            "thay_doi_%": round(((cur - prev) / abs(prev)) * 100, 2) if prev else 0.0,
        }
    return deltas

COMPARE_FIELDS: List[str] = [field for field, _ in TABLE_FIELDS]

def generate_report_node(state: FinancialReportState) -> dict:
    metrics = state.get("period_metrics") or {}
    scope, fallback = select_scope(metrics)
    dataset = build_period_dataset(metrics) or fallback
    unit = state.get("currency_unit") or "VND_BILLION"
    chart_paths = list(state.get("chart_paths") or [])
    chart_map = state.get("chart_map") or {}
    symbol = state.get("symbol") or ""

    # Read data from temporary file paths instead of state
    import json
    import os

    # Read validation flags
    flags_all = []
    validation_flags_path = state.get("validation_flags_path")
    if validation_flags_path and os.path.exists(validation_flags_path):
        try:
            with open(validation_flags_path, 'r') as f:
                flags_all = json.load(f)
        except Exception:
            flags_all = list(state.get("validation_flags") or [])
    else:
        flags_all = list(state.get("validation_flags") or [])

    # Read ratios
    ratios_all = {}
    ratios_path = state.get("ratios_path")
    if ratios_path and os.path.exists(ratios_path):
        try:
            with open(ratios_path, 'r') as f:
                ratios_all = json.load(f)
        except Exception:
            ratios_all = state.get("ratios") or {}
    else:
        ratios_all = state.get("ratios") or {}

    # Read trends
    trends_all = {}
    trends_path = state.get("trends_path")
    if trends_path and os.path.exists(trends_path):
        try:
            with open(trends_path, 'r') as f:
                trends_all = json.load(f)
        except Exception:
            trends_all = state.get("trends") or {}
    else:
        trends_all = state.get("trends") or {}

    # Read health scores
    health_scores_all = {}
    health_scores_path = state.get("health_scores_path")
    if health_scores_path and os.path.exists(health_scores_path):
        try:
            with open(health_scores_path, 'r') as f:
                health_scores_all = json.load(f)
        except Exception:
            health_scores_all = state.get("health_scores") or {}
    else:
        health_scores_all = state.get("health_scores") or {}

    # Read forecasts
    forecasts_all = {}
    forecasts_path = state.get("forecasts_path")
    if forecasts_path and os.path.exists(forecasts_path):
        try:
            with open(forecasts_path, 'r') as f:
                forecasts_all = json.load(f)
        except Exception:
            forecasts_all = state.get("forecasts") or {}
    else:
        forecasts_all = state.get("forecasts") or {}

    # Read prediction intervals
    prediction_intervals_all = {}
    prediction_intervals_path = state.get("prediction_intervals_path")
    if prediction_intervals_path and os.path.exists(prediction_intervals_path):
        try:
            with open(prediction_intervals_path, 'r') as f:
                prediction_intervals_all = json.load(f)
        except Exception:
            prediction_intervals_all = state.get("prediction_intervals") or {}
    else:
        prediction_intervals_all = state.get("prediction_intervals") or {}

    # Read scenarios
    scenarios_all = {}
    scenarios_path = state.get("scenarios_path")
    if scenarios_path and os.path.exists(scenarios_path):
        try:
            with open(scenarios_path, 'r') as f:
                scenarios_all = json.load(f)
        except Exception:
            scenarios_all = state.get("scenarios") or {}
    else:
        scenarios_all = state.get("scenarios") or {}

    # Read narrative store
    narratives_all = []
    narrative_store_path = state.get("narrative_store_path")
    if narrative_store_path and os.path.exists(narrative_store_path):
        try:
            with open(narrative_store_path, 'r') as f:
                narratives_all = json.load(f)
        except Exception:
            narratives_all = state.get("narrative_store") or []
    else:
        narratives_all = state.get("narrative_store") or []

    reconciliation_all = state.get("scope_reconciliation") or []

    if not dataset:
        report = assemble_report_markdown(
            "_Không có dữ liệu._", {}, {}, {}, [], chart_paths,
            symbol=symbol, scope=scope, unit=unit, chart_map=chart_map,
        )
        return {"narrative_mda": "", "narratives_mda": {}, "final_report_md": report, "final_reports": {}}

    reports: Dict[str, str] = {}
    narratives: Dict[str, str] = {}
    for period_key in sorted(dataset.keys(), key=period_sort_key):
        period_scope = select_period_data(metrics, period_key)[0] or scope
        previous_key = previous_period_key(dataset, period_key)
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
        )
        narratives[period_key] = narrative
        reports[period_key] = assemble_report_markdown(
            narrative, period_dataset, period_ratios, period_trends, period_flags,
            chart_paths, slice_reconciliation(reconciliation_all, period_key),
            narrative_store_path=state.get("narrative_store_path"),
            symbol=symbol, scope=period_scope, unit=unit, chart_map=chart_map,
            period_key=period_key, previous_period=previous_key,
            health_score=health_scores_all.get(period_key),
            forecasts=forecasts_all,
            prediction_intervals=prediction_intervals_all,
            scenarios=scenarios_all,
        )

    first_key = sorted(reports.keys(), key=period_sort_key)[0]
    return {
        "narrative_mda": narratives.get(first_key, ""),
        "narratives_mda": narratives,
        "final_report_md": reports[first_key],
        "final_reports": reports,
    }

def build_report_node(state: FinancialReportState) -> dict:
    reports = state.get("final_reports") or {}
    batch_id = str(state.get("batch_id") or "unknown")
    out_dir = os.path.join("example_output", batch_id)
    os.makedirs(out_dir, exist_ok=True)

    if not reports:
        reports = {batch_id: state.get("final_report_md", "")}

    output_paths: List[str] = []
    for period_key, report_md in sorted(reports.items(), key=lambda item: period_sort_key(item[0])):
        period_dir = os.path.join(out_dir, str(period_key))
        os.makedirs(period_dir, exist_ok=True)
        output_path = os.path.join(period_dir, f"Bao_Cao_{period_key}.md")
        with open(output_path, "w", encoding="utf-8") as fh:
            fh.write(report_md)
        output_paths.append(output_path)

    return {
        "output_report_path": output_paths[0] if output_paths else None,
        "output_report_paths": output_paths,
    }

def review_report_node(state: FinancialReportState) -> dict:
    reports = state.get("final_reports") or {}
    if reports:
        preview = "\n\n".join(
            f"### Kỳ {period_key}\n{(report_md or '')[:400]}"
            for period_key, report_md in sorted(reports.items(), key=lambda item: period_sort_key(item[0]))
        )[:1200]
    else:
        preview = (state.get("final_report_md") or "")[:1200]
    decision = interrupt({
        "type": "review_output",
        "message": "Duyệt báo cáo cuối? (approve/retry/abort)",
        "periods": sorted(reports.keys(), key=period_sort_key),
        "report_preview": preview,
        "flags": list(state.get("validation_flags") or [])[:10],
    })

    choice = "approve"
    if isinstance(decision, dict):
        value = decision.get("decision") or decision.get("choice") or decision.get("approved")
        if isinstance(value, bool):
            choice = "approve" if value else "abort"
        elif isinstance(value, str):
            choice = value.strip().lower()
    elif isinstance(decision, str):
        choice = decision.strip().lower()
    elif isinstance(decision, bool):
        choice = "approve" if decision else "abort"

    if choice in ("retry", "edit", "redo", "again"):
        choice = "retry"
    elif choice in ("abort", "reject", "no", "n", "cancel", "stop"):
        choice = "abort"
    else:
        choice = "approve"
    return {"review_decision": choice}

def route_after_report_review(state: FinancialReportState) -> str:
    decision = str(state.get("review_decision") or "approve").lower()
    if decision == "retry":
        return "generate_report"
    if decision == "abort":
        return "end"
    return "build_report"