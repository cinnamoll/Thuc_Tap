import os
import re
from typing import Any, Dict, Tuple
import pdfplumber

from Class.FinancialState import FinancialReportState
from Class.NotesExtraction.FinancialNotes import FinancialNotesExtractor
from Class.TableExtractor import TableExtractor

KEYWORD_MAP = {
    "doanh_thu": [r"net\s*revenue", r"total\s*revenue", r"sales"],
    "loi_nhuan_sau_thue": [r"net\s*(?:income|profit)", r"profit\s*after\s*tax"],
    "tong_tai_san": [r"total\s*assets"],
    "von_chu_so_huu": [r"(?:owner'?s?\s*)?equity"],
    "no_phai_tra": [r"total\s*liabilities", r"liabilities"],
}

def extract_financial_figures(text: str) -> dict:
    data: Dict[str, float] = {}
    for field, patterns in KEYWORD_MAP.items():
        for pattern in patterns:
            match = re.search(pattern + r"[:\s]*([0-9][0-9.,\s]*)", text, re.IGNORECASE)
            if not match:
                continue
            raw_num = match.group(1).replace(" ", "").replace(",", "")
            if raw_num.count(".") > 1:
                raw_num = raw_num.replace(".", "")
            try:
                data[field] = float(raw_num)
            except ValueError:
                continue
            break
    return data

def normalize_ranges(raw: Any) -> Dict[str, Tuple[int, int]]:
    out: Dict[str, Tuple[int, int]] = {}
    if not isinstance(raw, dict):
        return out
    for key, value in raw.items():
        if isinstance(value, (list, tuple)) and len(value) == 2:
            try:
                out[str(key)] = (int(value[0]), int(value[1]))
            except (TypeError, ValueError):
                continue
    return out

_INT64_MAX = 2 ** 63 - 1

def msgpack_safe(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: msgpack_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [msgpack_safe(v) for v in obj]
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, int):
        return float(obj) if not (-_INT64_MAX - 1 <= obj <= _INT64_MAX) else obj
    if isinstance(obj, float):
        if obj != obj or obj in (float("inf"), float("-inf")):
            return None
    return obj

def extraction_worker_node(state: FinancialReportState) -> dict:
    state = dict(state or {})
    file_path = state.get("path") or state.get("file_path") or ""
    year = state.get("year")
    symbol = state.get("symbol") or "UNKNOWN"
    scope = state.get("scope")
    period_key = state.get("period_key")
    ranges = normalize_ranges(state.get("ranges"))

    result: Dict[str, Any] = {
        "file_id": state.get("file_id") or os.path.basename(file_path),
        "source_file": state.get("raw_filename") or os.path.basename(file_path),
        "symbol": symbol,
        "year": year,
        "period_key": period_key,
        "scope": scope,
        "lang": state.get("lang"),
        "circular": state.get("circular"),
        "ranges": {k: list(v) for k, v in ranges.items()},
        "error": None,
        "warnings": [],
    }

    bs_obj = pl_obj = cf_obj = notes_obj = None
    keyword_figures: Dict[str, float] = {}

    if not file_path or not ranges:
        result["error"] = "missing file_path or ranges"
    else:
        extractor = TableExtractor()
        try:
            if "BS" in ranges:
                bs_obj = extractor.extract_balance_sheet(file_path, ranges["BS"][0], ranges["BS"][1], year, scope, period_key)
            if "IS" in ranges:
                pl_obj = extractor.extract_income_statement(file_path, ranges["IS"][0], ranges["IS"][1], year, scope, period_key)
            if "CF" in ranges:
                cf_obj = extractor.extract_cash_flow(file_path, ranges["CF"][0], ranges["CF"][1], year, scope, period_key)
            if "NOTES" in ranges:
                notes_obj = FinancialNotesExtractor().extract_notes_structured(file_path, ranges["NOTES"][0], ranges["NOTES"][1], year, scope, period_key)
            result["warnings"] = extractor.warnings[:20]
        except Exception as exc:
            result["error"] = f"{type(exc).__name__}: {exc}"

    if bs_obj is None and pl_obj is None and cf_obj is None and file_path:
        try:
            with pdfplumber.open(file_path) as reader:
                full_text = "\n".join((p.extract_text() or "") for p in reader.pages)
            keyword_figures = extract_financial_figures(full_text)
        except Exception as exc:
            result["error"] = result.get("error") or f"{type(exc).__name__}: {exc}"

    result["keyword_figures"] = keyword_figures
    result["statement_counts"] = {
        "balance_sheet_sections": len(bs_obj.sections) if bs_obj else 0,
        "balance_sheet_rows": sum(len(v) for v in bs_obj.sections.values()) if bs_obj else 0,
        "income_statement_rows": len(pl_obj.line_items) if pl_obj else 0,
        "cash_flow_rows": sum(len(v) for v in cf_obj.sections.values()) if cf_obj else 0,
        "notes_tables": len(notes_obj.table_metadata or {}) if notes_obj else 0,
    }

    out: Dict[str, Any] = {"extracted_data": [result]}
    if bs_obj is not None:
        out["balance_data"] = [bs_obj.model_dump()]
    if pl_obj is not None:
        out["income_data"] = [pl_obj.model_dump()]
    if cf_obj is not None:
        out["cash_data"] = [cf_obj.model_dump()]
    if notes_obj is not None:
        notes_dump = notes_obj.model_dump()
        notes_dump["tables"] = notes_obj.get_all_tables()
        out["financial_data"] = [notes_dump]
    return msgpack_safe(out)