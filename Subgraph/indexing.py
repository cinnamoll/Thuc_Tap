import os
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import pdfplumber
from collections import Counter

from Class.FinancialState import FinancialReportState
from Class.TableExtractor import fold_text, folded_contains

BS_KEY = ("balancesheet", "statementoffinancialposition", "bangcandoiketoan")
IS_KEY = ("incomestatement", "statementofcomprehensiveincome", "ketquahoatdongkinhdoanh")
CF_KEY = ("cashflowstatement", "statementofcashflows", "baocaoluuchuyentiente")
NOTES_KEY = ("notestofinancialstatements", "notestoconsolidatedfinancialstatements", "notestotheconsolidatedfinancialstatements", "thuyetminhbaocaotaichinh")

QUARTER_ROMAN = {"i": 1, "ii": 2, "iii": 3, "iv": 4}
INDEX_PAGE_SKIP = 3

@dataclass
class StatementLocation:
    file_id: str
    path: str
    raw_filename: str
    symbol: str
    tax_code: str
    year: Optional[int]
    quarter: Optional[int]
    period_key: str
    scope: str
    lang: str
    form: str
    circular: str
    unit: str
    num_pages: int
    ranges: Dict[str, Tuple[int, int]] = field(default_factory=dict)
    extraction_method: str = "content_scan"
    company_name: str = ""
    entity_id: str = ""

    def as_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["ranges"] = {k: list(v) for k, v in self.ranges.items()}
        return d

def first_page(compacts: List[str], keys, start: int = 0) -> Optional[int]:
    for i in range(max(0, start), len(compacts)):
        for k in keys:
            if folded_contains(compacts[i], k):
                return i
    return None

def detect_period_from_cover(text: str) -> Tuple[Optional[int], Optional[int]]:
    t = text or ""
    patterns_roman = [
        r"Quarter\s*(I{1,3}|IV|V?I{0,3})\s*,?\s*(\d{4})",  
        r"QUÝ\s*(I{1,3}|IV|V?I{0,3})\s*/?\s*(\d{4})",      
    ]
    for pat in patterns_roman:
        m = re.search(pat, t, re.I)
        if m and m.group(1):
            q = QUARTER_ROMAN.get(m.group(1).lower())
            if q:
                return int(m.group(2)), q
            
    patterns_num = [
        r"Quarter\s*(\d{1,2})\s*/\s*(\d{4})",
        r"Quý\s*(\d{1,2})\s*/?\s*(\d{4})",
    ]
    for pat in patterns_num:
        m = re.search(pat, t, re.I)
        if m and 1 <= int(m.group(1)) <= 4:
            return int(m.group(2)), int(m.group(1))
    m = re.search(r"(20\d{2})", t)
    return (int(m.group(1)) if m else None), None

def detect_period(file_path: str, cover_text: str) -> Tuple[Optional[int], Optional[int]]:
    stem = os.path.splitext(os.path.basename(file_path))[0]
    year = quarter = None

    m = re.search(r"[_\-]q([1-4])[_\-](\d{4})", stem, re.I)
    if m:
        quarter, year = int(m.group(1)), int(m.group(2))
    else:
        m = re.search(r"quy[_\-]?([1-4])", stem, re.I)
        if m:
            quarter = int(m.group(1))

    if year is None or quarter is None:
        cy, cq = detect_period_from_cover(cover_text)
        year = year or cy
        quarter = quarter or cq

    if year is None:
        m = re.search(r"(20\d{2})", stem)
        year = int(m.group(1)) if m else None
    return year, quarter

def detect_company_name(cover_text: str, compacts: List[str] = None) -> str:
    lines = [line.strip() for line in (cover_text or "").split("\n") if line.strip()]
    if not lines:
        return ""

    for line in lines[:5]:
        if re.search(r"(?:báo\s*cáo\s*tài\s*chính|financial\s*report|financial\s*statements|bảng\s*cân\s*đối|mẫu\s*số|form\s*no|mst|mmsstt|quy|quarter)", line, re.I):
            continue
        if re.search(r"(?:công\s*ty|tổng\s*công\s*ty|tập\s*đoàn|ngân\s*hàng|joint\s*stock|corporation|company|jsc|ltd)", line, re.I):
            return line

    if lines and len(lines[0]) > 3 and not re.search(r"(?:báo\s*cáo|financial\s*statements|mẫu\s*số|form|trang|page)", lines[0], re.I):
        return lines[0]
    return ""

def detect_symbol(compacts: List[str], cover_text: str, raw_pages: List[str] = None) -> Tuple[str, str]:
    tax = ""
    m = re.search(r"(?:MST|MMSSTT)[:\s]*(\d{9,13})", (cover_text or "") + " " + " ".join(compacts[:3]), re.I)
    if m:
        tax = m.group(1)

    for c in compacts:
        m = re.search(r"(?:stockcode|macophieu|machungkhoan)(?:la|is)?([a-z]{2,6})", c)
        if m and m.group(1).upper() not in ("NOTE", "NOTES", "THE", "AND", "FOR", "VND", "USD", "CONG", "TY", "NAM", "BAO", "CAO"):
            return m.group(1).upper(), tax

    if raw_pages:
        for t in raw_pages:
            m = re.search(r"(?:mã\s+(?:chứng\s+khoán|cổ\s+phiếu)|stock\s+code|ticker(?:\s+symbol)?)\s*(?:là|is|:)?\s*([A-Za-z]{2,6})\b", t, re.I)
            if m and m.group(1).upper() not in ("NOTE", "NOTES", "THE", "AND", "FOR", "VND", "USD", "CONG", "TY", "NAM", "BAO", "CAO"):
                return m.group(1).upper(), tax

    return "UNKNOWN", tax

def locate_ranges(compacts: List[str]) -> Dict[str, Tuple[int, int]]:
    n = len(compacts)
    balance = first_page(compacts, BS_KEY, INDEX_PAGE_SKIP)
    income = first_page(compacts, IS_KEY, (balance + 1) if balance is not None else INDEX_PAGE_SKIP)
    cash_flow = first_page(compacts, CF_KEY, (income + 1) if income is not None else INDEX_PAGE_SKIP)

    if balance is None and (income is not None or cash_flow is not None):
        balance = INDEX_PAGE_SKIP
    if income is None and cash_flow is not None:
        income = max((balance + 1) if balance is not None else 0, cash_flow - 1)
    if cash_flow is None and income is not None:
        cash_flow = income + 1
    if balance is None or income is None or cash_flow is None or cash_flow >= n:
        return {}

    return {"BS": (balance, max(balance, income - 1)), "IS": (income, income), "CF": (cash_flow, cash_flow), "NOTES": (cash_flow + 1, n - 1),}

def detect_scope(compacts: List[str], ranges: Dict[str, Tuple[int, int]]) -> str:
    for key in ("BS", "IS", "CF"):
        if key not in ranges:
            continue
        i = ranges[key][0]
        if any(folded_contains(compacts[i], k) for k in ("consolidated", "hopnhat")):
            return "consolidated"
    return "separate"

def detect_lang(compacts: List[str], ranges: Dict[str, Tuple[int, int]]) -> str:
    for key in ("BS", "IS", "CF"):
        if key not in ranges:
            continue
        i = ranges[key][0]
        if any(folded_contains(compacts[i], k) for k in ("bangcandoiketoan", "ketquahoatdongkinhdoanh", "baocaoluuchuyentiente")):
            return "vi"
    return "en"

def detect_form_and_circular(raw_pages: List[str], ranges: Dict[str, Tuple[int, int]]) -> Tuple[str, str]:
    page_text = raw_pages[ranges["BS"][0]] if "BS" in ranges and ranges["BS"][0] < len(raw_pages) else ""

    form = ""
    m = re.search(r"(?:Form\s*No|Mẫu\s*số)[^A-Za-z0-9]*B\s*(0?\d)\s*-?\s*DN", page_text, re.I)
    if m:
        form = "B{:02d}".format(int(m.group(1)))

    circular = ""
    m = re.search(r"Circular\s*(?:No\.?)?\s*(\d{1,3}/\d{4})", page_text, re.I)
    if m:
        circular = m.group(1)
    else:
        m = re.search(r"Thông\s*tư\s*số\s*(\d{1,3}/\d{4})", page_text, re.I)
        if m:
            circular = m.group(1)
    return form, circular

def detect_currency_unit(raw_pages: List[str], ranges: Dict[str, Tuple[int, int]]) -> str:
    locations_to_check = []

    if len(raw_pages) >= 2:
        locations_to_check.extend(raw_pages[:2])
    elif len(raw_pages) >= 1:
        locations_to_check.append(raw_pages[0])

    if "BS" in ranges and ranges["BS"][0] < len(raw_pages):
        bs_start, bs_end = ranges["BS"]
        for i in range(max(0, bs_start - 1), min(len(raw_pages), bs_end + 2)):
            locations_to_check.append(raw_pages[i])

    # 3. Notes section
    if "NOTES" in ranges and ranges["NOTES"][0] < len(raw_pages):
        notes_start, notes_end = ranges["NOTES"]
        for i in range(notes_start, min(len(raw_pages), notes_start + 3)):
            locations_to_check.append(raw_pages[i])

    seen = set()
    unique_locations = []
    for text in locations_to_check:
        if text not in seen:
            seen.add(text)
            unique_locations.append(text)

    SCALE_UNITS = {"nghìn": "VND_THOUSAND", "ngàn": "VND_THOUSAND", "triệu": "VND_MILLION", "tỷ": "VND_BILLION"}
    CURRENCY_PATTERNS = [
        (r"(nghìn|ngàn|triệu|tỷ)\s*(?:đồng|VND|VNĐ)", lambda m: SCALE_UNITS.get(m.group(1).lower(), "VND")),
        (r"(?:Currency\s*unit|Đơn\s*vị\s*tính|Currency)\s*:?\s*([A-Za-zĐđ]{3,7})", lambda m: m.group(1).upper()),
        (r"(?:Tỷ\s*Đồng|tỷ\s*đồng)", lambda m: "VND_BILLION"),
        (r"(?:Triệu\s*Đồng|triệu\s*đồng)", lambda m: "VND_MILLION"),
        (r"(?:Nghìn\s*Đồng|nghìn\s*đồng)", lambda m: "VND_THOUSAND"),
    ]

    for page_text in unique_locations:
        if not page_text:
            continue

        for pattern, converter in CURRENCY_PATTERNS:
            m = re.search(pattern, page_text, re.I)
            if m:
                return converter(m)

    return "VND"

def build_batch_node(state: FinancialReportState) -> dict:
    return {"batch_id": f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"}

def index_files_node(state: FinancialReportState) -> dict:
    input_files = state.get("input_files", []) or []
    plan: List[Dict[str, Any]] = []

    for path in input_files:
        with pdfplumber.open(path) as pdf:
            raw = [p.dedupe_chars().extract_text() or "" for p in pdf.pages]
        compacts = [fold_text(t) for t in raw]

        cover = "\n".join(raw[:2])
        year, quarter = detect_period(path, cover)
        symbol, tax_code = detect_symbol(compacts, cover, raw)
        company_name = detect_company_name(cover, compacts)
        entity_id = symbol if symbol != "UNKNOWN" else tax_code
        ranges = locate_ranges(compacts)
        scope = detect_scope(compacts, ranges) if ranges else "unknown"
        lang = detect_lang(compacts, ranges) if ranges else "en"
        form, circular = detect_form_and_circular(raw, ranges)
        unit = detect_currency_unit(raw, ranges)

        if year and quarter:
            period_key = f"{year}Q{quarter}"
        elif year:
            period_key = str(year)
        else:
            period_key = "UNKNOWN"

        loc = StatementLocation(
            file_id=os.path.basename(path),
            path=path,
            raw_filename=os.path.basename(path),
            symbol=symbol,
            tax_code=tax_code,
            year=year,
            quarter=quarter,
            period_key=period_key,
            scope=scope,
            lang=lang,
            form=form,
            circular=circular,
            unit=unit,
            num_pages=len(raw),
            ranges=ranges,
            extraction_method="title_scan_after_index",
            company_name=company_name,
            entity_id=entity_id,
        )
        plan.append(loc.as_dict())

    known_symbols = [it.get("symbol") for it in plan if it.get("symbol") and it.get("symbol") != "UNKNOWN"]
    known_companies = [it.get("company_name") for it in plan if it.get("company_name")]

    if known_symbols:
        symbol_counts = Counter(known_symbols)
        fallback_symbol = symbol_counts.most_common(1)[0][0]
    else:
        fallback_symbol = state.get("symbol") or ""

    if known_companies:
        company_counts = Counter(known_companies)
        fallback_company = company_counts.most_common(1)[0][0]

        vn_companies = [c for c in known_companies if re.search(r"(?:công\s*ty|cổ\s*phần|tập\s*đoàn)", c, re.I)]
        if vn_companies:
            vn_company_counts = Counter(vn_companies)
            fallback_company = vn_company_counts.most_common(1)[0][0]
    else:
        fallback_company = state.get("company_name") or ""

    for it in plan:
        if it.get("symbol") == "UNKNOWN" and fallback_symbol != "UNKNOWN":
            it["symbol"] = fallback_symbol
        if not it.get("company_name") and fallback_company:
            it["company_name"] = fallback_company
        if not it.get("entity_id") or it.get("entity_id") == "UNKNOWN":
            it["entity_id"] = it.get("symbol") if it.get("symbol") != "UNKNOWN" else (it.get("tax_code") or "")

    file_metadata = [
        {
            "file_path": item["path"],
            "symbol": item["symbol"],
            "company_name": item["company_name"],
            "entity_id": item["entity_id"],
            "period_key": item["period_key"]
        }
        for item in plan
    ]

    resolved_symbol = fallback_symbol if fallback_symbol != "UNKNOWN" else (state.get("symbol") or "")
    resolved_company = fallback_company or (state.get("company_name") or "")
    resolved_entity_id = resolved_symbol or (state.get("entity_id") or "")
    if not resolved_entity_id:
        known_taxes = [it.get("tax_code") for it in plan if it.get("tax_code")]
        if known_taxes:
            resolved_entity_id = known_taxes[0]

    return {
        "extraction_plan": plan,
        "input_files": input_files,
        "file_metadata": file_metadata,  
        "symbol": resolved_symbol,
        "company_name": resolved_company,
        "entity_id": resolved_entity_id,
    }

def select_files_node(state: FinancialReportState) -> dict:
    plan = state.get("extraction_plan", []) or []
    grouped: Dict[str, Dict[str, Dict[str, Any]]] = {}

    for item in plan:
        if not item.get("ranges"):
            continue
        key = item.get("period_key") or "UNKNOWN"
        grouped.setdefault(key, {})[item.get("scope", "unknown")] = item

    period_index: List[Dict[str, Any]] = []
    for period_key, scopes in grouped.items():
        preferred = "consolidated" if "consolidated" in scopes else sorted(scopes)[0]
        for scope, item in scopes.items():
            period_index.append({
                "period_key": period_key,
                "year": item.get("year"),
                "quarter": item.get("quarter"),
                "scope": scope,
                "file_id": item.get("file_id"),
                "lang": item.get("lang"),
                "circular": item.get("circular"),
                "preferred": scope == preferred,
            })

    period_index.sort(key=lambda p: (p.get("year") or 0, p.get("quarter") or 0, p.get("scope") or ""))
    return {"period_index": period_index}