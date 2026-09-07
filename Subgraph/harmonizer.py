import re
from typing import Any, Dict, List

from Class.FinancialState import FinancialReportState
from Class.NotesExtraction.FinancialNotes import FinancialNotesExtractor

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
    except ValueError:
        return 0.0

def is_numeric_literal(val: Any) -> bool:
    """Only true for actual numbers / numeric strings (with separators,
    parentheses-negative, or percent). Excludes narrative cells such as
    'Historical cost' or 'Dec. 31, 2025'."""
    if isinstance(val, (int, float)):
        return True
    if not isinstance(val, str):
        return False
    s = val.strip()
    if not s:
        return False
    s = s.rstrip("%")
    if s.startswith("(") and s.endswith(")"):
        s = s[1:-1]
    s = s.replace(",", "").replace(".", "").replace(" ", "").replace("\u00a0", "")
    cleaned = re.sub(r"[()%,.\- ]", "", val)
    return cleaned.isdigit()

def schema_harmonizer(state: FinancialReportState) -> dict:
    numeric_df: List[Dict[str, Any]] = []
    narrative_store: List[Dict[str, Any]] = []

    batch_id = state.get("batch_id", "UNKNOWN")
    
    balance_data = state.get("balance_data", [])
    for bs in balance_data:
        year = bs.year
        page = bs.page_start
        for sec_name, lines in bs.sections.items():
            for line in lines:
                row_label = line.chi_tieu
                code = line.ma_so
                note_id = line.thuyet_minh

                metrics = [("so_cuoi_ky", "current_year"), ("so_dau_nam", "prior_year")]
                for attr, metric_name in metrics:
                    val = getattr(line, attr, None)
                    if is_valid_value(val):
                        numeric_df.append({
                            "report_type": "balance_sheet",
                            "note_id": note_id,
                            "note_title": None,
                            "note_type": None,
                            "row_label": row_label,
                            "code": code,
                            "period": year,
                            "metric": metric_name,
                            "value": parse_value(val),
                            "source_page": page,
                            "batch_id": batch_id
                        })

    income_data = state.get("income_data", [])
    for ist in income_data:
        year = ist.year
        page = ist.page_start
        for line in ist.line_items:
            row_label = line.chi_tieu
            code = line.ma_so
            note_id = line.thuyet_minh

            metrics = [
                ("ky_nay", "current_year"), 
                ("ky_truoc", "prior_year"),
                ("luy_ke_ky_nay", "accum_current"),
                ("luy_ke_ky_truoc", "accum_prior")
            ]
            for attr, metric_name in metrics:
                val = getattr(line, attr, None)
                if is_valid_value(val):
                    numeric_df.append({
                        "report_type": "income_statement",
                        "note_id": note_id,
                        "note_title": None,
                        "note_type": None,
                        "row_label": row_label,
                        "code": code,
                        "period": year,
                        "metric": metric_name,
                        "value": parse_value(val),
                        "source_page": page,
                        "batch_id": batch_id
                    })

    cash_data = state.get("cash_data", [])
    for cfs in cash_data:
        year = cfs.year
        page = cfs.page_start
        for sec_name, lines in cfs.sections.items():
            for line in lines:
                row_label = line.chi_tieu
                code = line.ma_so
                note_id = line.thuyet_minh

                metrics = [
                    ("luy_ke_ky_nay", "current_year"), 
                    ("luy_ke_ky_truoc", "prior_year")
                ]
                for attr, metric_name in metrics:
                    val = getattr(line, attr, None)
                    if is_valid_value(val):
                        numeric_df.append({
                            "report_type": "cash_flow",
                            "note_id": note_id,
                            "note_title": None,
                            "note_type": None,
                            "row_label": row_label,
                            "code": code,
                            "period": year,
                            "metric": metric_name,
                            "value": parse_value(val),
                            "source_page": page,
                            "batch_id": batch_id
                        })

    notes_data = state.get("financial_data", [])
    notes_ext = FinancialNotesExtractor()
    
    for note in notes_data:
        year = note.year
        page = note.page_start
        if not note.tables:
            continue

        table_keys = set()
        for heading, rows in note.tables.items():
            if not rows or not isinstance(rows, list):
                continue
            if not notes_ext.is_valid_section_key(heading):
                continue

            prose_rows = [r for r in rows if isinstance(r, dict) and set(r.keys()) == {"text"}]
            numeric_rows = [r for r in rows if not (isinstance(r, dict) and set(r.keys()) == {"text"})]

            note_id_tuple = notes_ext.parse_section_key(heading)
            note_id_str = str(note_id_tuple[0]) if note_id_tuple[0] != 999 else ""
            if note_id_tuple[0] != 999 and note_id_tuple[1] != 0:
                note_id_str += f".{note_id_tuple[1]}"
            m = notes_ext.SECTION_NO.match(heading)
            section_num = m.group(1) if m else ""
            note_type = notes_ext.map_heading_to_section(section_num)

            if numeric_rows:
                table_keys.add(note_id_tuple)
                note_title = heading
                for row in numeric_rows:
                    if not isinstance(row, dict):
                        continue
                    row_label = row.get("Items") or row.get("chi_tieu") or ""
                    code = row.get("Code") or row.get("ma_so") or ""

                    for key, val in row.items():
                        if key in ["Items", "chi_tieu", "Code", "ma_so", "Notes", "thuyet_minh", "Prefix", "prefix"]:
                            continue
                        if is_valid_value(val) and is_numeric_literal(val):
                            numeric_df.append({
                                "report_type": "notes",
                                "note_id": note_id_str,
                                "note_title": note_title,
                                "note_type": note_type,
                                "row_label": str(row_label),
                                "code": str(code),
                                "period": year,
                                "metric": key,
                                "value": parse_value(val),
                                "source_page": page,
                                "batch_id": batch_id
                            })

            if prose_rows:
                if note_id_tuple in table_keys and note_id_tuple != (999, 0):
                    continue
                for tr in prose_rows:
                    narrative_store.append({
                        "note_id": note_id_str,
                        "note_title": heading,
                        "text": tr.get("text", "")
                    })

    note_id_to_title = {}
    for row in numeric_df:
        if row["report_type"] == "notes" and row["note_id"]:
            existing_title = note_id_to_title.get(row["note_id"])
            if existing_title and existing_title != row["note_title"]:
                row["note_title"] = existing_title
            else:
                note_id_to_title[row["note_id"]] = row["note_title"]
    
    return {"harmonized_dataset": numeric_df, "narrative_store": narrative_store}