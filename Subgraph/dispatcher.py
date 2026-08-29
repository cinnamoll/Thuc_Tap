import os
import re
import uuid
from datetime import datetime
from langgraph.types import Send
from Class.FinancialState import FinancialReportState

def generate_batch_id(state: FinancialReportState) -> dict:
    return {"batch_id": f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"}

def pdf_dispatcher(state: FinancialReportState) -> dict:
    input_files = state.get("input_files", [])
    tasks = []

    for idx, path in enumerate(input_files):
        filename = os.path.basename(path)
        name_no_ext = os.path.splitext(os.path.basename(filename))[0]
        parts = name_no_ext.split('_')

        info = {
            "file_path": path,
            "raw_filename": filename,
            "symbol": None,
            "year": None,
            "quarter_or_period": None,
            "scope": "Không xác định",    
            "is_signed": False,
            "hash_id": None,
            "lang": "vi"
        }

        name_lower = name_no_ext.lower()

        if "signed" in name_lower or "ks" in parts:
            info["is_signed"] = True
            
        if any(k in name_lower for k in ["hopnhat", "hn", "consolidated"]):
            info["scope"] = "Hợp nhất"
        elif any(k in name_lower for k in ["rieng", "congtyme", "seperate", "_r_"]):
            info["scope"] = "Riêng (Công ty mẹ)"

        period_match = re.search(r'(q[1-4]|ban_nien|kiem_toan)', name_lower)
        if period_match:
            info["quarter_or_period"] = period_match.group(1).upper()
        year_match = re.search(r'(20\d{2}|19\d{2})', filename)
        info["year"] = int(year_match.group(1)) if year_match else (2020 + idx)
        
        if parts[0].isdigit() and len(parts) > 1:
            info["symbol"] = parts[1].upper()
            if len(parts) > 6 and len(parts[5]) >= 6:  
                info["hash_id"] = parts[5]
        else:
            info["symbol"] = parts[0].upper()

        if any(k in parts for k in ["en", "eng"]):
            info["lang"] = "en"
        elif any(k in parts for k in ["vn", "vi"]):
            info["lang"] = "vi"
        
        tasks.append(info)

    return {"dispatched_tasks": tasks}

def route_to_extraction_workers(state: FinancialReportState) -> list[Send]:
    return [Send("extraction_worker", task) for task in state.get("dispatched_tasks", [])]