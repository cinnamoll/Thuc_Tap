import re
from typing import Any, Dict, List, Optional

from Class.FinancialState import FinancialReportState
from Class.NotesExtraction.FinancialNotes import FinancialNotesExtractor
from Subgraph.code_mapping import code_to_name

def is_valid_value(val: Any) -> bool:
    if val is None:
        return False
    if isinstance(val, (int, float)):
        return True
    if isinstance(val, str) and val.strip() == "":
        return False
    return True

def parse_value(val: Any) -> float:
    if val is None or (isinstance(val, str) and val.strip() == ""):
        return 0.0
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0

def is_numeric_literal(val: Any) -> bool:
    if isinstance(val, (int, float)):
        return True
    if not isinstance(val, str):
        return False
    s = val.strip()
    if not s:
        return False
    return re.sub(r"[()%,.\-\s\u00a0]", "", s).isdigit()

NOTE_LABEL_KEYS = {"Items", "chi_tieu", "Code", "ma_so", "Notes", "notes", "thuyet_minh", "Prefix", "prefix", "title"}

def row_data(meta: Dict[str, Any], *, statement_type: str, report_type: str, label: str,
         code: Optional[str], metric: str, value: float, source_page: Any,
         note_id: Optional[str] = None, note_title: Optional[str] = None,
         note_type: Optional[str] = None) -> Dict[str, Any]:
    year = meta.get("year")
    period_key = meta.get("period_key")
    return {
        "batch_id": meta.get("batch_id"),
        "source_file": meta.get("source_file"),
        "symbol": meta.get("symbol"),
        "scope": meta.get("scope"),
        "lang": meta.get("lang"),
        "statement_type": statement_type,
        "report_type": report_type,
        "period_key": period_key,
        "period": period_key,
        "fiscal_year": year,
        "year": year,
        "note_id": note_id,
        "note_title": note_title,
        "note_type": note_type,
        "row_label": label,
        "code": code,
        "line_item_canonical": code_to_name(report_type, code, label),
        "metric": metric,
        "value": value,
        "source_page": source_page,
    }

def meta_index(state: FinancialReportState) -> Dict[Any, Dict[str, Any]]:
    idx: Dict[Any, Dict[str, Any]] = {}
    for item in state.get("extracted_data") or []:
        if isinstance(item, dict):
            idx[(item.get("scope"), item.get("period_key"))] = item
    return idx

def schema_harmonizer(state: FinancialReportState) -> dict:
    rows: List[Dict[str, Any]] = []
    narrative_store: List[Dict[str, Any]] = []

    batch_id = state.get("batch_id", "UNKNOWN")
    meta_idx = meta_index(state)

    def meta_for(scope, period_key, period_year=None, source_file=None):
        meta = dict(meta_idx.get((scope, period_key)) or {})
        meta.setdefault("batch_id", batch_id)
        meta.setdefault("scope", scope)
        meta.setdefault("period_key", period_key)
        meta.setdefault("year", period_year)
        meta.setdefault("source_file", source_file)
        meta.setdefault("symbol", state.get("symbol"))
        return meta

    for bs in state.get("balance_data") or []:
        meta = meta_for(bs.get("scope"), bs.get("period_key"), bs.get("year"))
        for section, lines in (bs.get("sections") or {}).items():
            for line in lines or []:
                for attr in ("so_cuoi_ky", "so_dau_nam"):
                    val = line.get(attr)
                    if is_valid_value(val):
                        rows.append(row_data(meta, statement_type="balance_sheet", report_type="balance_sheet",
                                         label=line.get("chi_tieu") or "", code=line.get("ma_so"),
                                         metric=attr, value=parse_value(val), source_page=bs.get("page_start")))

    for ist in state.get("income_data") or []:
        meta = meta_for(ist.get("scope"), ist.get("period_key"), ist.get("year"))
        for line in ist.get("line_items") or []:
            for attr in ("ky_nay", "ky_truoc", "luy_ke_ky_nay", "luy_ke_ky_truoc"):
                val = line.get(attr)
                if is_valid_value(val):
                    rows.append(row_data(meta, statement_type="income_statement", report_type="income_statement",
                                     label=line.get("chi_tieu") or "", code=line.get("ma_so"),
                                     metric=attr, value=parse_value(val), source_page=ist.get("page_start")))

    for cf in state.get("cash_data") or []:
        meta = meta_for(cf.get("scope"), cf.get("period_key"), cf.get("year"))
        for section, lines in (cf.get("sections") or {}).items():
            for line in lines or []:
                for attr in ("luy_ke_ky_nay", "luy_ke_ky_truoc"):
                    val = line.get(attr)
                    if is_valid_value(val):
                        rows.append(row_data(meta, statement_type="cash_flow", report_type="cash_flow",
                                         label=line.get("chi_tieu") or "", code=line.get("ma_so"),
                                         metric=attr, value=parse_value(val), source_page=cf.get("page_start")))

    mapper = FinancialNotesExtractor().heading_mapper
    section_no_re = getattr(mapper, "SECTION_NO", None)
    
    for note in state.get("financial_data") or []:
        meta = meta_for(note.get("scope"), note.get("period_key"), note.get("year"))
        tables = note.get("tables") or {}
        if not tables:
            continue

        table_ids = set()
        for heading, table_rows in tables.items():
            if not table_rows or not isinstance(table_rows, list):
                continue
            if not mapper.is_valid_section_key(heading):
                continue

            prose_rows = [r for r in table_rows if isinstance(r, dict) and set(r.keys()) == {"text"}]
            numeric_rows = [r for r in table_rows if not (isinstance(r, dict) and set(r.keys()) == {"text"})]

            note_id_tuple = mapper.parse_section_key(heading)
            note_id = "" if note_id_tuple[0] == 999 else str(note_id_tuple[0])
            if note_id_tuple[0] != 999 and note_id_tuple[1] != 0:
                note_id = f"{note_id}.{note_id_tuple[1]}"
            match = section_no_re.match(heading) if section_no_re else None
            note_type = mapper.map_heading_to_section(match.group(1) if match else "")

            if numeric_rows:
                table_ids.add(note_id_tuple)
                for row in numeric_rows:
                    if not isinstance(row, dict):
                        continue
                    label = row.get("Items") or row.get("chi_tieu") or row.get("title") or ""
                    code = row.get("Code") or row.get("ma_so")
                    for key, val in row.items():
                        if key in NOTE_LABEL_KEYS:
                            continue
                        if is_valid_value(val) and is_numeric_literal(val):
                            rows.append(row_data(meta, statement_type="notes", report_type="notes",
                                             label=str(label), code=str(code) if code else None,
                                             metric=str(key), value=parse_value(val),
                                             source_page=note.get("page_start"), note_id=note_id,
                                             note_title=heading, note_type=note_type))

            if prose_rows:
                if note_id_tuple in table_ids and note_id_tuple != (999, 0):
                    continue
                for tr in prose_rows:
                    narrative_store.append({
                        "note_id": note_id,
                        "note_title": heading,
                        "scope": meta.get("scope"),
                        "period_key": meta.get("period_key"),
                        "text": tr.get("text", ""),
                    })

    return {"harmonized_dataset": rows, "narrative_store": narrative_store}