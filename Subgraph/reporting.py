import os
from typing import Any, Dict, List, Optional
import matplotlib
import matplotlib.pyplot as plt
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_deepseek import ChatDeepSeek
from langgraph.types import interrupt

from Class.FinancialState import FinancialReportState
from Subgraph.ratio_trend import period_sort_key, select_scope

load_dotenv()
matplotlib.use("Agg")
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

def to_billion(value: Any, unit: str = "VND_BILLION") -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    if unit == "VND":
        return number / 1_000_000_000
    if unit == "VND_THOUSAND":
        return number / 1_000_000
    if unit == "VND_MILLION":
        return number / 1_000
    return number

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

def plot_metrics_by_period(dataset: Dict[str, Dict[str, float]], output_dir: str, unit: str = "VND_BILLION", filename: str = "trend_core.png") -> Optional[str]:
    keys = sorted((dataset or {}).keys(), key=period_sort_key)
    if not keys:
        return None
    
    os.makedirs(output_dir, exist_ok=True)
    revenue = [to_billion((dataset.get(k) or {}).get("doanh_thu") or 0.0, unit) for k in keys]
    profit = [to_billion((dataset.get(k) or {}).get("loi_nhuan_sau_thue") or 0.0, unit) for k in keys]

    fig, ax1 = plt.subplots(figsize=(9, 4))
    ax1.bar(keys, revenue, color="#3B82F6", alpha=0.75, label="Doanh thu")
    ax1.set_xlabel("Kỳ")
    ax1.set_ylabel("Doanh thu (tỷ VND)", color="#3B82F6")
    ax2 = ax1.twinx()
    ax2.plot(keys, profit, marker="D", color="#EF4444", linewidth=2, label="LNST")
    ax2.set_ylabel("Lợi nhuận sau thuế (tỷ VND)", color="#EF4444")
    plt.title("Doanh thu & Lợi nhuận sau thuế theo quý")
    plt.grid(True, alpha=0.3)
    ax1.tick_params(axis="x", rotation=45)
    path = os.path.join(output_dir, filename)
    fig.savefig(path, bbox_inches="tight", dpi=150)
    plt.close(fig)
    return path

def write_narrative_mda(dataset: Dict[str, Dict[str, float]], ratios: dict, trends: dict, flags: list, forecasts: dict = None, symbol: str = "", scope: str = "") -> str:
    # Prepare forecast information for the prompt
    forecast_info = ""
    if forecasts:
        forecast_info = "\n- Dự báo tài chính (tỷ VND): " + str(forecasts)

    prompt = f"""
    Viết báo cáo phân tích quản trị (MD&A) bằng tiếng Việt dựa trên dữ liệu sau.
    - Doanh nghiệp: {symbol or 'N/A'} - phạm vi báo cáo: {scope or 'N/A'}
    - Dữ liệu tài chính theo quý (đơn vị: tỷ VND): {dataset}
    - Chỉ số (ROE, ROA, Debt/Equity, Net Margin): {ratios}
    - Tăng trưởng QoQ/YoY/CAGR: {trends}
    - Cảnh báo & bất thường: {flags}{forecast_info}

    Yêu cầu: (1) đánh giá tổng quan sức khỏe tài chính theo quý; (2) phân tích
    nguyên nhân biến động và các cảnh báo kế toán; (3) phân tích xu hướng và dự báo futuro; (4) khuyến nghị ngắn gọn.
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
                             narrative_store: List[Dict[str, Any]] | None = None,
                             forecasts: dict = None,
                             scenarios: dict = None,
                             health_scores: dict = None,
                             symbol: str = "", scope: str = "", unit: str = "VND_BILLION") -> str:
    keys = sorted((dataset or {}).keys(), key=period_sort_key)
    report = [f"# BÁO CÁO PHÂN TÍCH TÀI CHÍNH — {symbol or 'DOANH NGHIỆP'}"]
    report.append(f"**Phạm vi dữ liệu:** {scope or 'n/a'} · **Số kỳ:** {len(keys)} ({keys[0] if keys else 'n/a'} → {keys[-1] if keys else 'n/a'}) · Đơn vị: tỷ VND\n")

    if health_scores and scope in health_scores:
        report.append("## 0. Dashboard Sức khỏe Tài chính & Đánh giá Rủi ro\n")
        scope_health = health_scores[scope]
        if keys and keys[-1] in scope_health:
            latest_health = scope_health[keys[-1]]
            report.append(f"- **Điểm sức khỏe tổng hợp ({keys[-1]}):** {latest_health.get('composite_score', 0)}/100")
            report.append(f"- **Phân loại rủi ro:** **{latest_health.get('risk_level', 'N/A')}**")
            report.append(f"- **Khả năng sinh lời:** {latest_health.get('profitability_score', 0)}/100 · **Đòn bẩy & An toàn:** {latest_health.get('leverage_score', 0)}/100 · **Dòng tiền:** {latest_health.get('cash_flow_score', 0)}/100\n")

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
        report.append("\n## 5. Dự báo tài chính\n")
        report.append("```json")
        report.append(f"{forecasts}")
        report.append("```")

    if scenarios:
        report.append("\n## 6. Phân tích Kịch bản & Kiểm tra Ứng xử (Stress Testing)\n")
        report.append("```json")
        report.append(f"{scenarios}")
        report.append("```")

    report.append("\n## 7. Cảnh báo Kế toán & Bất thường\n")
    if flags:
        for flag in flags:
            period = flag.get("period_key") or flag.get("year") or ""
            report.append(f"- **[{flag.get('severity', 'N/A')}]** {period} — {flag.get('message', '')}")
    else:
        report.append("Không ghi nhận bất thường kế toán hoặc vi phạm đẳng thức.")

    report.append("\n## 8. Biểu đồ\n")
    if chart_paths:
        for path in chart_paths:
            report.append(f"![Chart]({path})")
    else:
        report.append("_Không có biểu đồ._")

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


def generate_interactive_report_json(state: FinancialReportState) -> Dict[str, Any]:
    """
    Generate structured interactive report JSON payload for frontend exploration.
    """
    metrics = state.get("period_metrics") or {}
    scope, dataset = select_scope(metrics)
    return {
        "batch_id": state.get("batch_id"),
        "symbol": state.get("symbol"),
        "scope": scope,
        "dataset": dataset,
        "ratios": state.get("ratios") or {},
        "trends": state.get("trends") or {},
        "forecasts": state.get("financial_forecasts") or {},
        "scenarios": state.get("scenario_analysis_results") or {},
        "health_score": state.get("financial_health_score") or {},
        "flags": state.get("validation_flags") or []
    }


def generate_report_node(state: FinancialReportState) -> dict:
    metrics = state.get("period_metrics") or {}
    scope, dataset = select_scope(metrics)
    unit = state.get("currency_unit") or "VND_BILLION"
    batch_id = str(state.get("batch_id") or "batch")
    out_dir = os.path.join("example_output", batch_id)
    chart_paths = list(state.get("chart_paths") or [])

    chart = plot_metrics_by_period(dataset, out_dir, unit)
    if chart:
        chart_paths.append(chart)

    flags = list(state.get("validation_flags") or [])
    narrative = write_narrative_mda(dataset, state.get("ratios") or {}, state.get("trends") or {},
                                    flags, state.get("financial_forecasts") or {},
                                    state.get("symbol") or "", scope)
    report = assemble_report_markdown(
        narrative, dataset, state.get("ratios") or {}, state.get("trends") or {}, flags,
        chart_paths, state.get("scope_reconciliation") or [], state.get("narrative_store") or [],
        forecasts=state.get("financial_forecasts") or {},
        scenarios=state.get("scenario_analysis_results") or {},
        health_scores=state.get("financial_health_score") or {},
        symbol=state.get("symbol") or "", scope=scope, unit=unit,
    )
    return {"narrative_mda": narrative, "final_report_md": report, "chart_paths": chart_paths}
    return {"narrative_mda": narrative, "final_report_md": report, "chart_paths": chart_paths}

def build_report_node(state: FinancialReportState) -> dict:
    report_md = state.get("final_report_md", "")
    batch_id = str(state.get("batch_id") or "unknown")
    out_dir = os.path.join("example_output", batch_id)
    os.makedirs(out_dir, exist_ok=True)
    output_path = os.path.join(out_dir, f"Bao_Cao_{batch_id}.md")
    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(report_md)
    return {"output_report_path": output_path}

def review_report_node(state: FinancialReportState) -> dict:
    decision = interrupt({
        "type": "review_output",
        "message": "Duyệt báo cáo cuối? (approve/retry/abort)",
        "report_preview": (state.get("final_report_md") or "")[:1200],
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