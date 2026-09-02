import re
from typing import Any, Dict, List

from Class.FinancialState import FinancialReportState
from Class.FinancialNotes import FinancialNotesExtractor

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
        if note.sections is None:
            raise ValueError(f"Fail-fast: FinancialNotesReport.sections is None for year {note.year}")
            
        year = note.year
        page = note.page_start
        table_keys = set()
        if note.tables:
            for heading, rows in note.tables.items():
                if not notes_ext.is_valid_section_key(heading):
                    continue
                
                note_id_tuple = notes_ext.parse_section_key(heading)
                table_keys.add(note_id_tuple)
                
                m = notes_ext.SECTION_NO.match(heading)
                section_num = m.group(1) if m else ""
                note_type = notes_ext.map_heading_to_section(section_num)
                
                note_id_str = str(note_id_tuple[0]) if note_id_tuple[0] != 999 else ""
                if note_id_tuple[0] != 999 and note_id_tuple[1] != 0:
                    note_id_str += f".{note_id_tuple[1]}"
                note_title = heading
                
                for row in rows:
                    row_label = row.get("Items") or row.get("chi_tieu") or ""
                    code = row.get("Code") or row.get("ma_so") or ""
                    
                    for key, val in row.items():
                        if key in ["Items", "chi_tieu", "Code", "ma_so", "Notes", "thuyet_minh", "Prefix", "prefix"]:
                            continue
                        
                        if is_valid_value(val):
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
                            
        if note.sections:
            for heading, contents in note.sections.items():
                if not contents or not isinstance(contents, list):
                    continue
                
                if not notes_ext.is_valid_section_key(heading):
                    continue
                    
                note_id_tuple = notes_ext.parse_section_key(heading)
                if note_id_tuple in table_keys and note_id_tuple != (999, 0):
                    continue
                    
                if "text" in contents[0]:
                    note_id_str = str(note_id_tuple[0]) if note_id_tuple[0] != 999 else ""
                    if note_id_tuple[0] != 999 and note_id_tuple[1] != 0:
                        note_id_str += f".{note_id_tuple[1]}"
                    
                    narrative_store.append({
                        "note_id": note_id_str,
                        "note_title": heading,
                        "text": contents[0]["text"]
                    })

    note_id_to_title = {}
    for row in numeric_df:
        if row["report_type"] == "notes" and row["note_id"]:
            existing_title = note_id_to_title.get(row["note_id"])
            if existing_title and existing_title != row["note_title"]:
                row["note_title"] = existing_title
            else:
                note_id_to_title[row["note_id"]] = row["note_title"]
    
    return {
        "harmonized_dataset": numeric_df,
        "narrative_store": narrative_store
    }