import os
import re
import pdfplumber

from Class.FinancialState import FinancialReportState
from Class.FinancialNotes import FinancialNotesExtractor
from Class.FinancialTable import FinancialTableExtractor

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

def iter_table_rows(tables):
    if tables is None:
        return
    if hasattr(tables, "to_dict") and hasattr(tables, "columns"):
        for rec in tables.to_dict(orient="records"):
            yield rec
        return
    if isinstance(tables, list):
        for rec in tables:
            if isinstance(rec, dict):
                yield rec
        return
    if isinstance(tables, dict):
        for value in tables.values():
            yield from iter_table_rows(value)

def figures_from_tables(tables, code_map: dict) -> dict:
    rows = list(iter_table_rows(tables))
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
        "doanh_thu": [r"doanh\s*thu(?:\s*thu[aầ]n)?", r"net\s*revenue", r"total\s*revenue", r"sales"],
        "loi_nhuan_sau_thue": [r"l[oợ]i\s*nhu[aậ]n\s*sau\s*thu[eế]", r"net\s*(?:income|profit)", r"profit\s*after\s*tax"],
        "tong_tai_san": [r"t[oổ]ng\s*t[aà]i\s*s[aả]n", r"total\s*assets"],
        "von_chu_so_huu": [r"v[oố]n\s*ch[uủ]\s*s[oở]\s*h[uữ]u", r"(?:owner'?s?\s*)?equity", r"vcsh"],
        "no_phai_tra": [r"n[oợ]\s*ph[aả]i\s*tr[aả]", r"total\s*liabilities", r"liabilities"],
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
        ("BS", re.compile(r"(?:Bảng\s+cân\s+đối\s+kế\s+toán|Balance\s+Sheet)[.\s…\-─_]*(\d+)", re.IGNORECASE)),
        ("PL", re.compile(r"(?:Báo\s+cáo\s+kết\s+quả\s+hoạt\s+động|Income\s+Statement|Kết\s+quả\s+hoạt\s+động\s+kinh\s+doanh)[.\s…\-─_]*(\d+)", re.IGNORECASE)),
        ("CF", re.compile(r"(?:Báo\s+cáo\s+lưu\s+chuyển\s+tiền\s+tệ|Cash\s+Flow|Lưu\s+chuyển\s+tiền\s+tệ)[.\s…\-─_]*(\d+)", re.IGNORECASE)),
        ("NOTES", re.compile(r"(?:Bản\s+thuyết\s+minh|Thuyết\s+minh\s+báo\s+cáo|Notes\s+to)[.\s…\-─_]*(\d+)", re.IGNORECASE)),
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
        ("BS", re.compile(r"(?:BẢNG\s+CÂN\s+ĐỐI\s+KẾ\s+TOÁN|CONSOLIDATED\s+BALANCE\s+SHEET|BALANCE\s+SHEET)", re.IGNORECASE)),
        ("PL", re.compile(r"(?:BÁO\s+CÁO\s+KẾT\s+QUẢ\s+HOẠT\s+ĐỘNG|INCOME\s+STATEMENT|STATEMENT\s+OF\s+(?:COMPREHENSIVE\s+)?INCOME)", re.IGNORECASE)),
        ("CF", re.compile(r"(?:BÁO\s+CÁO\s+LƯU\s+CHUYỂN\s+TIỀN\s+TỆ|CASH\s+FLOWS?\s+STATEMENT|STATEMENT\s+OF\s+CASH\s+FLOWS)", re.IGNORECASE)),
        ("NOTES", re.compile(r"(?:BẢN\s+THUYẾT\s+MINH|THUYẾT\s+MINH\s+BÁO\s+CÁO|NOTES\s+TO\s+THE\s+(?:CONSOLIDATED\s+)?FINANCIAL\s+STATEMENTS)", re.IGNORECASE)),
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

def extract_balance_sheet_pages(text: str, page_start: int, page_end: int, year: int) -> BalanceSheet:
    raw_bs = FinancialTableExtractor().extract_balance_sheet(text)
 
    bs = BalanceSheet(page_start=page_start, page_end=page_end, year=year)
    bs.raw_data = serialize_tables(raw_bs)
 
    BS_CODE = {"tong_tai_san": ["270"], "no_phai_tra": ["300", "330"], "von_chu_so_huu": ["400", "410"]}

    figures = figures_from_tables(raw_bs, BS_CODE)
    bs.tong_tai_san = parse_number(figures.get("tong_tai_san"))
    bs.no_phai_tra = parse_number(figures.get("no_phai_tra"))
    bs.von_chu_so_huu = parse_number(figures.get("von_chu_so_huu"))
 
    sections = {}
    for part_key, part_data in raw_bs.items():
        lines = []
        for sub_key, sub_df in part_data.items():
            for rec in serialize_tables(sub_df):
                if isinstance(rec, dict) and rec.get("Chỉ tiêu"):
                    lines.append(BalanceSheetLine(
                        prefix=rec.get("Prefix"),
                        chi_tieu=rec.get("Chỉ tiêu", ""),
                        ma_so=rec.get("Mã số"),
                        so_cuoi_ky=parse_number(rec.get("Số cuối kỳ")),
                        so_dau_nam=parse_number(rec.get("Số đầu năm")),
                    ))
        if lines:
            sections[part_key] = lines
    bs.sections = sections
 
    return bs

def extract_income_statement_pages(text: str, page_start: int, page_end: int, year: int) -> IncomeStatement:
    raw_pl = FinancialTableExtractor().extract_income_statement(text)
 
    pl = IncomeStatement(page_start=page_start, page_end=page_end, year=year)
    pl.raw_data = serialize_tables(raw_pl)
 
    line_items = []
    for rec in serialize_tables(raw_pl):
        if isinstance(rec, dict) and rec.get("Chỉ tiêu"):
            line_items.append(IncomeStatementLine(
                stt=rec.get("STT"),
                chi_tieu=rec.get("Chỉ tiêu", ""),
                ma_so=rec.get("Mã số"),
                ky_nay=parse_number(rec.get("Kỳ này")),
                ky_truoc=parse_number(rec.get("Kỳ trước")),
            ))
    pl.line_items = line_items
 
    PL_CODE = {"doanh_thu": ["01", "10"], "loi_nhuan_sau_thue": ["60", "62"]}
 
    figures = figures_from_tables(raw_pl, PL_CODE)
    pl.doanh_thu = figures.get("doanh_thu")
    pl.loi_nhuan_sau_thue = figures.get("loi_nhuan_sau_thue")
 
    kw = extract_financial_figures(text)
    if pl.doanh_thu is None:
        pl.doanh_thu = kw.get("doanh_thu")
    if pl.loi_nhuan_sau_thue is None:
        pl.loi_nhuan_sau_thue = kw.get("loi_nhuan_sau_thue")
 
    return pl

def extract_cash_flow_pages(text: str, page_start: int, page_end: int, year: int) -> CashFlowStatement:
    raw_cf = FinancialTableExtractor().extract_cash_flow(text)
 
    cf = CashFlowStatement(page_start=page_start, page_end=page_end, year=year)
    cf.raw_data = serialize_tables(raw_cf)
 
    sections = {}
    for section_key, section_df in raw_cf.items():
        lines = []
        for rec in serialize_tables(section_df):
            if isinstance(rec, dict) and rec.get("Chỉ tiêu"):
                lines.append(CashFlowLine(
                    prefix=rec.get("Prefix"),
                    chi_tieu=rec.get("Chỉ tiêu", ""),
                    ma_so=rec.get("Mã số"),
                    luy_ke_ky_nay=parse_number(rec.get("Lũy kế kỳ này")),
                    luy_ke_ky_truoc=parse_number(rec.get("Lũy kế kỳ trước")),
                ))
        if lines:
            sections[section_key] = lines
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
        CONTENTS_PATTERN = re.compile(
            r"(?:MỤC\s+LỤC|TABLE\s+OF\s+CONTENTS|NỘI\s+DUNG|CONTENTS)",
            re.IGNORECASE,
        )
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
            bs_text = "\n".join(page_texts[ps : min(pe + 1, total_pages)])
            bs_obj = extract_balance_sheet_pages(bs_text, ps, pe, year)
            state['balance_data'].append(bs_obj)

        if "PL" in page_ranges:
            ps, pe = page_ranges["PL"]
            pl_text = "\n".join(page_texts[ps : min(pe + 1, total_pages)])
            pl_obj = extract_income_statement_pages(pl_text, ps, pe, year)
            state['income_data'].append(bs_obj)

        if "CF" in page_ranges:
            ps, pe = page_ranges["CF"]
            cf_text = "\n".join(page_texts[ps : min(pe + 1, total_pages)])
            cf_obj = extract_cash_flow_pages(cf_text, ps, pe, year)
            state['cash_data'].append(bs_obj)
            
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