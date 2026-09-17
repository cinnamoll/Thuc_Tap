from typing import List, Dict, Any
import os
from dotenv import load_dotenv
from langchain_deepseek import ChatDeepSeek
from langchain_core.messages import HumanMessage, SystemMessage
import json

from Subgraph.charts import SUBSECTION_TITLES, to_billion
from Subgraph.ratio_trend import period_sort_key

load_dotenv()
llm = ChatDeepSeek(model="deepseek-v4-flash", temperature=0)

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

COMPARE_FIELDS: List[str] = [field for field, _ in TABLE_FIELDS]

DEFAULT_BILINGUAL_TAGS: List[Dict[str, str]] = [
    {"vi": "vốn chủ sở hữu âm", "en": "negative equity"},
    {"vi": "rủi ro hoạt động liên tục", "en": "going concern risk"},
    {"vi": "hệ số thanh toán ngắn hạn", "en": "current ratio"},
    {"vi": "phải thu khó đòi", "en": "doubtful debt provision"},
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

def write_narrative_mda(dataset: Dict[str, Dict[str, float]], ratios: dict, trends: dict, flags: list, symbol: str = "", scope: str = "", period_key: str = "", previous_period: str = "", previous_data: dict = None, deltas: dict = None, feedback_context: str = "") -> str:
    feedback_prompt = f"\n    - LƯU Ý / YÊU CẦU ĐIỀU CHỈNH TỪ LẦN REVIEW TRƯỚC: {feedback_context}\n" if feedback_context else ""
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
    - Cảnh báo & bất thường: {flags}{feedback_prompt}

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
                             narrative_store: List[Dict[str, Any]] | None = None,
                             symbol: str = "", scope: str = "", unit: str = "VND_BILLION",
                             chart_map: Dict[str, List[str]] | None = None,
                             period_key: str = "", previous_period: str = "") -> str:
    keys = sorted((dataset or {}).keys(), key=period_sort_key)
    report = [f"# BÁO CÁO PHÂN TÍCH TÀI CHÍNH — {symbol or 'DOANH NGHIỆP'}"]
    if period_key:
        compare = f" · **So sánh với:** {previous_period}" if previous_period else ""
        report.append(f"**Phạm vi dữ liệu:** {scope or 'n/a'} · **Kỳ:** {period_key}{compare} · Đơn vị: tỷ VND\n")
    else:
        report.append(f"**Phạm vi dữ liệu:** {scope or 'n/a'} · **Số kỳ:** {len(keys)} ({keys[0] if keys else 'n/a'} → {keys[-1] if keys else 'n/a'}) · Đơn vị: tỷ VND\n")

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

def build_yaml_front_matter(symbol: str, period_key: str, scope: str, unit: str, batch_id: str, input_files: List[str] = None,
                            previous_key: str = "", next_key: str = "", flags: List[Dict[str, Any]] = None, review_status: str = "approved",
                            report_version: int = 1, company_name: str = "", entity_id: str = "") -> str:
    flags_list = flags or []
    has_flags = len(flags_list) > 0
    missing_prior = not bool(previous_key)

    data_quality_flags = {
        "unit_mismatch_suspected": False,
        "missing_prior_period": missing_prior,
        "missing_financial_notes": False,
        "accounting_checks_passed": not has_flags,
    }

    effective_entity_id = entity_id or symbol
    yaml_lines = [
        "---",
        f"entity_id: {json.dumps(effective_entity_id, ensure_ascii=False) if effective_entity_id else 'null'}",
        f"company_name: {json.dumps(company_name, ensure_ascii=False) if company_name else 'null'}",
        f"symbol: {json.dumps(symbol, ensure_ascii=False) if symbol else 'null'}",
        f"period_key: {json.dumps(period_key)}",
        f"scope: {json.dumps(scope or 'separate')}",
        f"currency_unit: {json.dumps(unit or 'ty_vnd')}",
        'circular: "200"',
        'lang: "vi"',
        f"batch_id: {json.dumps(batch_id)}",
        f"source_files: {json.dumps(input_files or [])}",
        "generated_at: null",
        f"report_version: {report_version}",
        f"review_status: {json.dumps(review_status)}",
        f"prev_period_file: {json.dumps(f'Bao_Cao_{previous_key}_RAG.md') if previous_key else 'null'}",
        f"next_period_file: {json.dumps(f'Bao_Cao_{next_key}_RAG.md') if next_key else 'null'}",
        "data_quality_flags:",
    ]
    for k, v in data_quality_flags.items():
        yaml_lines.append(f"  {k}: {str(v).lower()}")
    yaml_lines.append("---")
    return "\n".join(yaml_lines)

def build_json_structured_block(period_data: Dict[str, float], ratios: Dict[str, Any], trends: Dict[str, Any], previous_key: str = "") -> str:
    cur_data = period_data or {}
    bs_data = {
        "total_assets": cur_data.get("tong_tai_san"),
        "short_term_assets": cur_data.get("tai_san_ngan_han"),
        "long_term_assets": cur_data.get("tai_san_dai_han"),
        "total_liabilities": cur_data.get("no_phai_tra"),
        "equity": cur_data.get("von_chu_so_huu"),
        "unit": "ty_vnd",
    }
    is_data = {
        "revenue": cur_data.get("doanh_thu"),
        "gross_profit": cur_data.get("loi_nhuan_gop"),
        "net_profit": cur_data.get("loi_nhuan_sau_thue"),
        "unit": "ty_vnd",
    }
    
    first_pk = next(iter(cur_data.keys()), "") if isinstance(cur_data, dict) else ""
    ratio_data = {
        "roe": (ratios.get("ROE") or {}).get(first_pk) if isinstance(ratios.get("ROE"), dict) else None,
        "roa": (ratios.get("ROA") or {}).get(first_pk) if isinstance(ratios.get("ROA"), dict) else None,
        "debt_to_equity": (ratios.get("Debt_to_Equity") or {}).get(first_pk) if isinstance(ratios.get("Debt_to_Equity"), dict) else None,
        "net_margin": (ratios.get("Net_Margin") or {}).get(first_pk) if isinstance(ratios.get("Net_Margin"), dict) else None,
        "unit": "percent_or_ratio",
    }

    growth_data = {
        "qoq": trends.get("qoq") if trends else None,
        "yoy": trends.get("yoy") if trends else None,
        "cagr": trends.get("cagr") if trends else None,
        "reason_null": "no_prior_period_data" if not previous_key else None,
    }

    structured = {
        "balance_sheet": bs_data,
        "income_statement": is_data,
        "ratios": ratio_data,
        "growth": growth_data,
    }
    return json.dumps(structured, indent=2, ensure_ascii=False)

def assemble_rag_report_markdown(
    narrative: str,
    dataset: Dict[str, Dict[str, float]],
    ratios: dict,
    trends: dict,
    flags: list,
    chart_paths: List[str],
    scope_reconciliation: List[Dict[str, Any]] | None = None,
    narrative_store: List[Dict[str, Any]] | None = None,
    symbol: str = "",
    scope: str = "",
    unit: str = "VND_BILLION",
    chart_map: Dict[str, List[str]] | None = None,
    period_key: str = "",
    previous_period: str = "",
    next_period: str = "",
    batch_id: str = "",
    input_files: List[str] = None,
    review_status: str = "approved",
    report_version: int = 1,
    company_name: str = "",
    entity_id: str = "",
) -> str:
    keys = sorted((dataset or {}).keys(), key=period_sort_key)
    period_data = (dataset or {}).get(period_key) or {}

    report = []
    yaml_header = build_yaml_front_matter(
        symbol=symbol,
        period_key=period_key,
        scope=scope,
        unit=unit,
        batch_id=batch_id,
        input_files=input_files,
        previous_key=previous_period,
        next_key=next_period,
        flags=flags,
        review_status=review_status,
        report_version=report_version,
        company_name=company_name,
        entity_id=entity_id,
    )
    report.append(yaml_header)
    report.append(f"\n# BÁO CÁO PHÂN TÍCH TÀI CHÍNH (RAG OPTIMIZED) — {symbol or 'DOANH NGHIỆP'}\n")

    report.append("## 0. Khối dữ liệu cấu trúc (Structured Data JSON)\n")
    report.append("```json")
    report.append(build_json_structured_block(period_data, ratios, trends, previous_period))
    report.append("```\n")

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
    if trends:
        report.append(json.dumps(trends, indent=2, ensure_ascii=False))
    else:
        report.append(json.dumps({"growth": None, "reason": "no_prior_period_data" if not previous_period else "missing_data"}, indent=2))
    report.append("```")

    report.append(f"\n## {"5. Kiểm định đẳng thức kế toán (deterministic)"}\n")
    if flags:
        for flag in flags:
            period = flag.get("period_key") or flag.get("year") or ""
            report.append(f"- **[{flag.get('severity', 'N/A')}]** {period} — {flag.get('message', '')}")
    else:
        report.append("Đã qua kiểm định: Không ghi nhận bất thường kế toán hoặc vi phạm đẳng thức.")

    report.extend(render_chart_section(chart_map, chart_paths))

    report.append(f"\n## {"8. Đánh giá rủi ro tài chính tổng hợp (LLM-generated)"}\n")
    report.append(narrative or "_Đánh giá rủi ro tài chính tổng hợp từ mô hình phân tích định tính._")

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
        report.append("_Không đủ dữ liệu để đối chiếu (cần cả bản riêng và hợp nhất)._")

    report.append("\n## Phụ lục B — Thuyết minh trọng yếu\n")
    narratives = narrative_store or []
    if narratives:
        for item in narratives[:15]:
            title = item.get("note_title") or item.get("note_id") or ""
            text = (item.get("text") or "").strip().replace("\n", " ")
            report.append(f"- **{title}** ({item.get('period_key', '')}): {text[:300]}")
    else:
        report.append("_Không có đoạn thuyết minh nào được trích (Reason: no_notes_extracted_from_source)._")

    report.append("\n## Retrieval Tags (Từ khóa song ngữ)\n")
    report.append("```yaml")
    report.append("tags:")
    for tag in DEFAULT_BILINGUAL_TAGS:
        report.append(f"  - {{vi: \"{tag['vi']}\", en: \"{tag['en']}\"}}")
    report.append("```")

    return "\n".join(report)