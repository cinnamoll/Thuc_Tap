import json
import re
from typing import Any
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_deepseek import ChatDeepSeek
from langgraph.types import Command

from Class.FinancialState import FinancialReportState
from Class.ReportResponse import FeedbackCategory, RejectionAnalysis

load_dotenv()
llm = ChatDeepSeek(model="deepseek-v4-flash")

VALID_TARGET_NODES = {
    "canonicalize_metrics",
    "accounting_check",
    "financial_forecasting",
    "ratio_trend_engine",
    "select_files_node",
    "generate_report",
    "review_report",
}

DEFAULT_MAX_RETRIES = 3
DEFAULT_CONFIDENCE_THRESHOLD = 0.6

INTERPRET_FEEDBACK_SYSTEM_PROMPT = """Bạn là Chuyên gia Phân tích Phản hồi Báo cáo Tài chính.
Nhiệm vụ của bạn là phân tích lý do người dùng từ chối/yêu cầu sửa báo cáo (rejection_reason) và xác định node cần quay lại trong pipeline LangGraph.

Các node hợp lệ (VALID_TARGET_NODES) và trách nhiệm:
1. "canonicalize_metrics": Sai số liệu thô / mapping chỉ tiêu kế toán VAS.
2. "accounting_check": Bảng cân đối kế toán, kết quả kinh doanh, lưu chuyển tiền tệ không khớp (BS/IS/CF), vi phạm kiểm định kiểm toán.
3. "financial_forecasting": Sai công thức dự báo, giả định forecast không phù hợp.
4. "ratio_trend_engine": Sai tính toán tỷ số tài chính (ROE, ROA, Debt/Equity, Net Margin) hoặc xu hướng.
5. "select_files_node": Chọn sai file PDF, sai kỳ báo cáo (quý/năm), nhầm bản riêng và hợp nhất.
6. "generate_report": Chỉ sai văn phong, thiếu nhận xét diễn giải MD&A mà không sai số liệu.
7. "review_report": Yêu cầu không thể tự sửa (out_of_scope), thông tin không rõ ràng hoặc cần con người xử lý.

Các danh mục (category):
- "data_error": Sai số liệu / mapping VAS (Target: "canonicalize_metrics")
- "validation_miss": BS/IS/CF không khớp, lỗi kiểm định (Target: "accounting_check")
- "calc_error": Sai công thức forecast / tỷ số (Target: "financial_forecasting" hoặc "ratio_trend_engine")
- "scope_error": Sai kỳ báo cáo, nhầm bản riêng/hợp nhất (Target: "select_files_node")
- "narrative_only": Chỉ sai văn phong / diễn giải (Target: "generate_report")
- "out_of_scope": Không đủ căn cứ tự sửa (Target: "review_report")
"""

def parse_feedback_analysis(llm_output: Any) -> RejectionAnalysis:
    if isinstance(llm_output, RejectionAnalysis):
        return llm_output
    if isinstance(llm_output, dict):
        cat_str = llm_output.get("category", "out_of_scope")
        try:
            category = FeedbackCategory(cat_str)
        except ValueError:
            category = FeedbackCategory.OUT_OF_SCOPE
        target_node = llm_output.get("target_node", "review_report")
        if target_node not in VALID_TARGET_NODES:
            target_node = "review_report"
        return RejectionAnalysis(
            category=category,
            target_node=target_node,
            specific_issue=str(llm_output.get("specific_issue", "Phân tích phản hồi từ người dùng.")),
            affected_fields=list(llm_output.get("affected_fields", [])),
            confidence=float(llm_output.get("confidence", 0.8)),
        )
    return RejectionAnalysis(
        category=FeedbackCategory.OUT_OF_SCOPE,
        target_node="review_report",
        specific_issue="Không thể phân tích phản hồi.",
        affected_fields=[],
        confidence=0.0,
    )

def interpret_feedback_node(state: FinancialReportState) -> dict:
    retry_count = (state.get("retry_count") or 0) + 1
    max_retries = state.get("max_retries") or DEFAULT_MAX_RETRIES
    history = list(state.get("feedback_history") or [])
    rejection_reason = state.get("rejection_reason") or "Yêu cầu kiểm tra lại báo cáo."

    if retry_count > max_retries:
        analysis = RejectionAnalysis(
            category=FeedbackCategory.OUT_OF_SCOPE,
            target_node="review_report",
            specific_issue=f"Đã vượt quá số lần thử lại tối đa ({max_retries} lần). Chuyển về review_report.",
            affected_fields=[],
            confidence=1.0,
        )
        analysis_dict = analysis.model_dump() if hasattr(analysis, "model_dump") else analysis.dict()
        return {
            "retry_count": retry_count,
            "last_feedback_analysis": analysis_dict,
            "feedback_history": history + [analysis_dict],
            "feedback_context": analysis.specific_issue,
        }

    prompt_user = f"""
    Lý do từ chối: {rejection_reason}
    Phạm vi dữ liệu: {state.get('symbol', 'N/A')}
    Trích đoạn báo cáo hiện tại: {(state.get('final_report_md') or '')[:500]}
    Cảnh báo kế toán hiện có: {list(state.get('validation_flags') or [])[:5]}
    """

    try:
        structured_llm = llm.with_structured_output(RejectionAnalysis)
        res = structured_llm.invoke([
            SystemMessage(content=INTERPRET_FEEDBACK_SYSTEM_PROMPT),
            HumanMessage(content=prompt_user),
        ])
        analysis = parse_feedback_analysis(res)
    except Exception:
        try:
            res = llm.invoke([
                SystemMessage(content=INTERPRET_FEEDBACK_SYSTEM_PROMPT),
                HumanMessage(content=prompt_user + "\nTrả về JSON với các trường: category, target_node, specific_issue, affected_fields, confidence."),
            ])
            raw_text = getattr(res, "content", "")
            match = re.search(r"\{.*\}", raw_text, re.DOTALL)
            if match:
                parsed_json = json.loads(match.group(0))
                analysis = parse_feedback_analysis(parsed_json)
            else:
                analysis = RejectionAnalysis(
                    category=FeedbackCategory.NARRATIVE_ONLY if "văn phong" in rejection_reason.lower() else FeedbackCategory.OUT_OF_SCOPE,
                    target_node="generate_report" if "văn phong" in rejection_reason.lower() else "review_report",
                    specific_issue=rejection_reason[:200],
                    confidence=0.7,
                )
        except Exception:
            analysis = RejectionAnalysis(
                category=FeedbackCategory.OUT_OF_SCOPE,
                target_node="review_report",
                specific_issue="Không thể xử lý phản hồi từ LLM.",
                confidence=0.0,
            )

    if history:
        last_entry = history[-1]
        cat_val = analysis.category.value if hasattr(analysis.category, "value") else str(analysis.category)
        if last_entry.get("target_node") == analysis.target_node and last_entry.get("category") == cat_val:
            analysis = RejectionAnalysis(
                category=FeedbackCategory.OUT_OF_SCOPE,
                target_node="review_report",
                specific_issue=f"Phát hiện lặp lại 2 lần xử lý tại node '{analysis.target_node}'. Chuyển về review_report để xử lý thủ công.",
                affected_fields=analysis.affected_fields,
                confidence=1.0,
            )

    analysis_dict = analysis.model_dump() if hasattr(analysis, "model_dump") else analysis.dict()
    feedback_context = f"[SỬA BÁO CÁO] Lý do: {rejection_reason}. Vấn đề: {analysis.specific_issue}. Chỉ tiêu ảnh hưởng: {', '.join(analysis.affected_fields) if analysis.affected_fields else 'Tất cả'}."

    return {
        "retry_count": retry_count,
        "last_feedback_analysis": analysis_dict,
        "feedback_history": history + [analysis_dict],
        "feedback_context": feedback_context,
    }

def route_feedback_node(state: FinancialReportState) -> Command:
    analysis = state.get("last_feedback_analysis") or {}
    retry_count = state.get("retry_count") or 0
    max_retries = state.get("max_retries") or DEFAULT_MAX_RETRIES

    target_node = analysis.get("target_node") or "review_report"
    confidence = float(analysis.get("confidence") or 0.0)
    category = analysis.get("category")

    if retry_count > max_retries:
        return Command(goto="review_report")

    if target_node not in VALID_TARGET_NODES:
        return Command(goto="review_report")

    if confidence < DEFAULT_CONFIDENCE_THRESHOLD:
        return Command(goto="review_report")

    if category == FeedbackCategory.OUT_OF_SCOPE.value or category == "out_of_scope":
        return Command(goto="review_report")

    return Command(goto=target_node)
