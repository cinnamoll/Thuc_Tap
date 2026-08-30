import os
import re
import pdfplumber

from Class.FinancialState import FinancialReportState
from Class.FinancialNotes import FinancialNotesExtractor
from Class.DataDrivenTableExtractor import DataDrivenTableExtractor

from Class.ReportContent.BalanceSheet import BalanceSheet, BalanceSheetLine
from Class.ReportContent.CashFlowStatement import CashFlowStatement, CashFlowLine
from Class.ReportContent.FinancialNotesReport import FinancialNotesReport
from Class.ReportContent.IncomeStatement import IncomeStatement, IncomeStatementLine

def parse_number(val):
    if val is None:
        return None
    s = str(val).strip()
    if not s or s == "-":
        return None
    negative = s.startswith("(") and s.endswith(")")
    if negative:
        s = s[1:-1]
    s = s.replace(" ", "")
    if s.count(".") > 1 and "," not in s:
        s = s.replace(".", "")
    elif s.count(",") > 1 and "." not in s:
        s = s.replace(",", "")
    elif "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    try:
        number = float(s)
        return -number if negative else number
    except ValueError:
        return None

def serialize_tables(obj):
    if hasattr(obj, "to_dict") and hasattr(obj, "fillna"):
        return obj.fillna("").to_dict(orient="records")
    if isinstance(obj, dict):
        return {k: serialize_tables(v) for k, v in obj.items()}
    return obj

def figures_from_tables(tables, code_map: dict) -> dict:
    if tables is None:
        return
    
    rows = []
    stack = [tables]
    while stack:
        current = stack.pop()
        if current is None:
            continue
        if hasattr(current, "to_dict") and hasattr(current, "columns"):
            rows.extend(current.to_dict(orient="records"))
        elif isinstance(current, list):
            for item in current:
                if isinstance(item, dict):
                    rows.append(item)
        elif isinstance(current, dict):
            stack.extend(current.values())
    
    data = {}
    for field, codes in code_map.items():
        for row in rows:
            code = str(row.get("Mã số", "")).strip()
            if code not in codes:
                continue
            for col in ["Số cuối kỳ", "Kỳ này", "Lũy kế kỳ này"]:
                parsed = parse_number(row.get(col))
                if parsed is not None:
                    data[field] = parsed
                    break
            if field in data:
                break
    return data

def extract_financial_figures(text: str) -> dict:
    data = {}
    KEYWORD_MAP = {
        "doanh_thu": [r"net\s*revenue", r"total\s*revenue", r"sales"],
        "loi_nhuan_sau_thue": [r"net\s*(?:income|profit)", r"profit\s*after\s*tax"],
        "tong_tai_san": [r"total\s*assets"],
        "von_chu_so_huu": [r"(?:owner'?s?\s*)?equity"],
        "no_phai_tra": [r"total\s*liabilities", r"liabilities"],
    }
    
    for field, patterns in KEYWORD_MAP.items():
        for pattern in patterns:
            match = re.search(
                pattern + r"[:\s]*([0-9][0-9.,\s]*)",
                text,
                re.IGNORECASE,
            )
            if match:
                raw_num = match.group(1).replace(" ", "").replace(",", "")
                if raw_num.count(".") > 1:
                    raw_num = raw_num.replace(".", "")
                try:
                    data[field] = float(raw_num)
                except ValueError:
                    continue
                break
    return data

def parse_contents(toc_text: str, total_pages: int) -> dict:
    found = {} 
    CONTENTS_ENTRY_PATTERNS = [
        ("BS", re.compile(r"(?:Balance\s+Sheet)[.\s…\-─_]*(\d+)", re.IGNORECASE)),
        ("PL", re.compile(r"(?:Income\s+Statement)[.\s…\-─_]*(\d+)", re.IGNORECASE)),
        ("CF", re.compile(r"(?:Cash\s+Flow)[.\s…\-─_]*(\d+)", re.IGNORECASE)),
        ("NOTES", re.compile(r"(?:Notes\s+to)[.\s…\-─_]*(\d+)", re.IGNORECASE)),
    ]
    for key, pattern in CONTENTS_ENTRY_PATTERNS:
        match = pattern.search(toc_text)
        if match:
            found[key] = int(match.group(1))

    if not found:
        return {}

    sorted_entries = sorted(found.items(), key=lambda x: x[1])
    ranges = {}
    for i, (key, start_page) in enumerate(sorted_entries):
        page_start = start_page - 1
        if i + 1 < len(sorted_entries):
            page_end = sorted_entries[i + 1][1] - 2  
        else:
            page_end = total_pages - 1

        page_start = max(0, min(page_start, total_pages - 1))
        page_end = max(page_start, min(page_end, total_pages - 1))
        ranges[key] = (page_start, page_end)

    return ranges

def assign_page_ranges_by_markers(page_texts: list) -> dict:
    found = []  
    STATEMENT_MARKERS = [
        ("BS", re.compile(r"(?:CONSOLIDATED\s+BALANCE\s+SHEET|BALANCE\s+SHEET)", re.IGNORECASE)),
        ("PL", re.compile(r"(?:INCOME\s+STATEMENT|STATEMENT\s+OF\s+(?:COMPREHENSIVE\s+)?INCOME)", re.IGNORECASE)),
        ("CF", re.compile(r"(?:CASH\s+FLOWS?\s+STATEMENT|STATEMENT\s+OF\s+CASH\s+FLOWS)", re.IGNORECASE)),
        ("NOTES", re.compile(r"(?:NOTES\s+TO\s+THE\s+(?:CONSOLIDATED\s+)?FINANCIAL\s+STATEMENTS)", re.IGNORECASE)),
    ]

    for i, text in enumerate(page_texts):
        for key, pattern in STATEMENT_MARKERS:
            if pattern.search(text):
                if not any(k == key for _, k in found):
                    found.append((i, key))
                break
 
    if not found:
        return {}
 
    found.sort(key=lambda x: x[0])
    total = len(page_texts)
    ranges = {}
    for i, (page_idx, key) in enumerate(found):
        if i + 1 < len(found):
            end = found[i + 1][0] - 1
        else:
            end = total - 1
        ranges[key] = (page_idx, max(page_idx, end))
 
    return ranges

def extract_balance_sheet_pages(file_path: str, page_start: int, page_end: int, year: int) -> BalanceSheet:
    raw_bs = DataDrivenTableExtractor().extract_table(file_path, page_start, page_end, "BS")
 
    bs = BalanceSheet(page_start=page_start, page_end=page_end, year=year)
    bs.raw_data = raw_bs
 
    BS_CODE = {"tong_tai_san": ["270"], "no_phai_tra": ["300", "330"], "von_chu_so_huu": ["400", "410"]}

    # Tinh toan figure tu list dict
    data = {}
    for field, codes in BS_CODE.items():
        for row in raw_bs:
            code = str(row.get("Mã số", "")).strip()
            if code not in codes:
                continue
            for col in ["Số cuối kỳ", "Kỳ này", "Lũy kế kỳ này"]:
                if row.get(col) is not None:
                    data[field] = row[col]
                    break
            if field in data:
                break

    bs.tong_tai_san = data.get("tong_tai_san")
    bs.no_phai_tra = data.get("no_phai_tra")
    bs.von_chu_so_huu = data.get("von_chu_so_huu")
 
    sections = {}
    current_part = None
    lines = []
    
    for rec in raw_bs:
        prefix = rec.get("Prefix")
        if prefix in ["A", "B", "C", "D", "E"]:
            if current_part and lines:
                sections[current_part] = lines
            current_part = prefix
            lines = []
        if rec.get("Chỉ tiêu"):
            lines.append(BalanceSheetLine(
                prefix=prefix,
                chi_tieu=rec.get("Chỉ tiêu", ""),
                ma_so=rec.get("Mã số"),
                so_cuoi_ky=rec.get("Số cuối kỳ"),
                so_dau_nam=rec.get("Số đầu năm"),
            ))
            
    if current_part and lines:
        sections[current_part] = lines
    elif lines: # fallback neu khong co part
        sections["ALL"] = lines
        
    bs.sections = sections
 
    return bs

def extract_income_statement_pages(file_path: str, page_start: int, page_end: int, year: int, full_text: str) -> IncomeStatement:
    raw_pl = DataDrivenTableExtractor().extract_table(file_path, page_start, page_end, "PL")
 
    pl = IncomeStatement(page_start=page_start, page_end=page_end, year=year)
    pl.raw_data = raw_pl
 
    line_items = []
    for rec in raw_pl:
        if rec.get("Chỉ tiêu"):
            line_items.append(IncomeStatementLine(
                stt=rec.get("Prefix"),
                chi_tieu=rec.get("Chỉ tiêu", ""),
                ma_so=rec.get("Mã số"),
                ky_nay=rec.get("Kỳ này"),
                ky_truoc=rec.get("Kỳ trước"),
            ))
    pl.line_items = line_items
 
    PL_CODE = {"doanh_thu": ["01", "10"], "loi_nhuan_sau_thue": ["60", "62"]}
 
    data = {}
    for field, codes in PL_CODE.items():
        for row in raw_pl:
            code = str(row.get("Mã số", "")).strip()
            if code not in codes:
                continue
            for col in ["Số cuối kỳ", "Kỳ này", "Lũy kế kỳ này"]:
                if row.get(col) is not None:
                    data[field] = row[col]
                    break
            if field in data:
                break

    pl.doanh_thu = data.get("doanh_thu")
    pl.loi_nhuan_sau_thue = data.get("loi_nhuan_sau_thue")
 
    kw = extract_financial_figures(full_text)
    if pl.doanh_thu is None:
        pl.doanh_thu = kw.get("doanh_thu")
    if pl.loi_nhuan_sau_thue is None:
        pl.loi_nhuan_sau_thue = kw.get("loi_nhuan_sau_thue")
 
    return pl

def extract_cash_flow_pages(file_path: str, page_start: int, page_end: int, year: int) -> CashFlowStatement:
    raw_cf = DataDrivenTableExtractor().extract_table(file_path, page_start, page_end, "CF")
 
    cf = CashFlowStatement(page_start=page_start, page_end=page_end, year=year)
    cf.raw_data = raw_cf
 
    sections = {}
    current_section = None
    lines = []
    
    for rec in raw_cf:
        prefix = rec.get("Prefix")
        if prefix and re.match(r'^[IVX]+$', prefix):
            if current_section and lines:
                sections[current_section] = lines
            current_section = prefix
            lines = []
            
        if rec.get("Chỉ tiêu"):
            lines.append(CashFlowLine(
                prefix=prefix,
                chi_tieu=rec.get("Chỉ tiêu", ""),
                ma_so=rec.get("Mã số"),
                luy_ke_ky_nay=rec.get("Lũy kế kỳ này"),
                luy_ke_ky_truoc=rec.get("Lũy kế kỳ trước"),
            ))
            
    if current_section and lines:
        sections[current_section] = lines
    elif lines:
        sections["ALL"] = lines
        
    cf.sections = sections
 
    return cf

def extract_notes_pages(text: str, page_start: int, page_end: int, year: int) -> FinancialNotesReport:
    raw_notes = FinancialNotesExtractor().extract_all_to_format(text)
 
    notes = FinancialNotesReport(page_start=page_start, page_end=page_end, year=year)
    notes.raw_data = raw_notes
 
    for section in raw_notes:
        if not isinstance(section, dict):
            continue
        for key, value in section.items():
            key_lower = key.lower()
            if "đặc điểm hoạt động" in key_lower:
                notes.dac_diem_hoat_dong = value if isinstance(value, dict) else {"noi_dung": str(value)}
            elif "kỳ kế toán" in key_lower:
                notes.ky_ke_toan_tien_te = str(value) if value else None
            elif "chuẩn mực" in key_lower:
                notes.chuan_muc_che_do = str(value) if value else None
            elif "hoạt động liên tục" in key_lower and "không" not in key_lower:
                notes.chinh_sach_hoat_dong_lien_tuc = str(value) if value else None
            elif "không đáp ứng" in key_lower or "không liên tục" in key_lower:
                notes.chinh_sach_khong_lien_tuc = str(value) if value else None
            elif "bảng cân đối" in key_lower:
                notes.bo_sung_bang_can_doi = value if isinstance(value, dict) else {"noi_dung": str(value)}
            elif "kết quả" in key_lower:
                notes.bo_sung_ket_qua_kd = str(value) if value else None
            elif "lưu chuyển tiền tệ" in key_lower:
                notes.bo_sung_luu_chuyen_tien_te = str(value) if value else None
            elif "thông tin khác" in key_lower or "những thông tin" in key_lower:
                notes.nhung_thong_tin_khac = value if isinstance(value, dict) else {"noi_dung": str(value)}
 
    return notes

def extraction_worker_node(state: FinancialReportState) -> dict:
    file_path = state.get("file_path", "")
    year = state.get("year", 2026)
    symbol = state.get("symbol")

    result = {
        "year": year,
        "file_path": file_path,
        "symbol": symbol,
        "origin": {
            "source_file": os.path.basename(file_path),
            "extraction_method": "page_based_toc",
        },
        "financial_data": {},
        "balance_sheet": {},
        "income_statement": [],
        "cash_flow": {},
        "notes": [],
        "error": None,
    }

    bs_obj = pl_obj = cf_obj = notes_obj = None

    with pdfplumber.open(file_path) as reader:
        total_pages = len(reader.pages)
        result["origin"]["num_pages"] = total_pages
        page_texts = [p.extract_text() or "" for p in reader.pages]

        contents_idx = None
        CONTENTS_PATTERN = re.compile(r"(?:TABLE\s+OF\s+CONTENTS|CONTENTS)", re.IGNORECASE)
        for i in range(min(10, total_pages)):
            if CONTENTS_PATTERN.search(page_texts[i]):
                contents_idx = i
                break

        page_ranges = {}
        if contents_idx is not None:
            toc_text = page_texts[contents_idx]
            if contents_idx + 1 < total_pages:
                toc_text += "\n" + page_texts[contents_idx + 1]
            page_ranges = parse_contents(toc_text, total_pages)
            result["origin"]["extraction_method"] = "page_based_contents"

        if not page_ranges or len(page_ranges) < 2:
            fallback_ranges = assign_page_ranges_by_markers(page_texts)
            for k, v in fallback_ranges.items():
                page_ranges.setdefault(k, v)
            if not page_ranges:
                result["origin"]["extraction_method"] = "page_based_markers"
            elif contents_idx is None:
                result["origin"]["extraction_method"] = "page_based_markers"
            else:
                result["origin"]["extraction_method"] = "page_based_contents+markers"

        financial_data = {}

        if "BS" in page_ranges:
            ps, pe = page_ranges["BS"]
            bs_obj = extract_balance_sheet_pages(file_path, ps, pe, year)
            state['balance_data'].append(bs_obj)

        if "PL" in page_ranges:
            ps, pe = page_ranges["PL"]
            full_text = "\n".join(page_texts)
            pl_obj = extract_income_statement_pages(file_path, ps, pe, year, full_text)
            state['income_data'].append(pl_obj)

        if "CF" in page_ranges:
            ps, pe = page_ranges["CF"]
            cf_obj = extract_cash_flow_pages(file_path, ps, pe, year)
            state['cash_data'].append(cf_obj)
            
        if "NOTES" in page_ranges:
            ps, pe = page_ranges["NOTES"]
            notes_text = "\n".join(page_texts[ps : min(pe + 1, total_pages)])
            notes_obj = extract_notes_pages(notes_text, ps, pe, year)
            state['financial_data'].append(bs_obj)
            
        core_fields = {
            "doanh_thu",
            "loi_nhuan_sau_thue",
            "tong_tai_san",
            "von_chu_so_huu",
            "no_phai_tra",
        }
        if not core_fields.issubset(financial_data.keys()):
            full_text = "\n".join(page_texts)
            kw_data = extract_financial_figures(full_text)
            for key, value in kw_data.items():
                financial_data.setdefault(key, value)

    output = {"extracted_data": [result]}
    if bs_obj:
        output["balance_sheet_obj"] = bs_obj.model_dump()
    if pl_obj:
        output["income_statement_obj"] = pl_obj.model_dump()
    if cf_obj:
        output["cash_flow_obj"] = cf_obj.model_dump()
    if notes_obj:
        output["notes_obj"] = notes_obj.model_dump()

    return output