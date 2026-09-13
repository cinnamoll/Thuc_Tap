import os
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import pdfplumber

from Class.FinancialState import FinancialReportState
from Class.TableExtractor import fold_text, folded_contains

SCOPE_CONSOLIDATED = "consolidated"
SCOPE_SEPARATE = "separate"

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

def detect_symbol(compacts: List[str], cover_text: str) -> Tuple[str, str]:
    """Trả (symbol, tax_code). Symbol lấy từ câu 'stock code CMI' trong Thuyết minh."""
    tax = ""
    m = re.search(r"MST[:\s]*(\d{9,13})", (cover_text or "") + " " + " ".join(compacts[:3]), re.I)
    if m:
        tax = m.group(1)

    for c in compacts:
        m = re.search(r"stockcode([a-z]{2,6})", c)
        if m and m.group(1).upper() not in ("NOTE", "NOTES"):
            return m.group(1).upper(), tax
    for c in compacts:
        m = re.search(r"macophieu([a-z]{2,6})", c)
        if m:
            return m.group(1).upper(), tax
    return "UNKNOWN", tax

def locate_ranges(compacts: List[str]) -> Dict[str, Tuple[int, int]]:
    n = len(compacts)
    bs = first_page(compacts, BS_KEY, INDEX_PAGE_SKIP)
    is_ = first_page(compacts, IS_KEY, (bs + 1) if bs is not None else INDEX_PAGE_SKIP)
    cf = first_page(compacts, CF_KEY, (is_ + 1) if is_ is not None else INDEX_PAGE_SKIP)

    if bs is None and (is_ is not None or cf is not None):
        bs = INDEX_PAGE_SKIP
    if is_ is None and cf is not None:
        is_ = max((bs + 1) if bs is not None else 0, cf - 1)
    if cf is None and is_ is not None:
        cf = is_ + 1
    if bs is None or is_ is None or cf is None or cf >= n:
        return {}

    return {"BS": (bs, max(bs, is_ - 1)), "IS": (is_, is_), "CF": (cf, cf), "NOTES": (cf + 1, n - 1),}

def detect_scope(compacts: List[str], ranges: Dict[str, Tuple[int, int]]) -> str:
    for key in ("BS", "IS", "CF"):
        if key not in ranges:
            continue
        i = ranges[key][0]
        if any(folded_contains(compacts[i], k) for k in ("consolidated", "hopnhat")):
            return SCOPE_CONSOLIDATED
    return SCOPE_SEPARATE

def detect_lang(compacts: List[str], ranges: Dict[str, Tuple[int, int]]) -> str:
    for key in ("BS", "IS", "CF"):
        if key not in ranges:
            continue
        i = ranges[key][0]
        if any(folded_contains(compacts[i], k) for k in ("bangcandoiketoan", "ketquahoatdongkinhdoanh", "baocaoluuchuyentiente")):
            return "vi"
    return "en"

def detect_form_and_circular(raw_pages: List[str], ranges: Dict[str, Tuple[int, int]]) -> Tuple[str, str]:
    """Đọc 'Form No: B 01 - DN' / 'Mẫu số: B 01 - DN' và số Thông tư áp dụng."""
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

def detect_unit(raw_pages: List[str], ranges: Dict[str, Tuple[int, int]]) -> str:
    page_text = raw_pages[ranges["BS"][0]] if "BS" in ranges and ranges["BS"][0] < len(raw_pages) else ""
    if not page_text:
        return "VND"

    SCALE_UNITS = {"nghìn": "VND_THOUSAND", "ngàn": "VND_THOUSAND", "triệu": "VND_MILLION", "tỷ": "VND_BILLION"}
    m = re.search(r"(nghìn|ngàn|triệu|tỷ)\s*(?:đồng|VND|VNĐ)", page_text, re.I)
    if m:
        return SCALE_UNITS.get(m.group(1).lower(), "VND")

    m = re.search(r"(?:Currency\s*unit|Đơn\s*vị\s*tính|Currency)\s*:?\s*([A-Za-zĐđ]{3,7})", page_text, re.I)
    if m:
        return m.group(1).upper()
    return "VND"

def build_batch(state: FinancialReportState) -> dict:
    return {"batch_id": f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"}

def index_files(state: FinancialReportState) -> dict:
    """Định danh mọi tệp đầu vào -> ``extraction_plan`` (mỗi tệp một StatementLocation)."""
    input_files = state.get("input_files", []) or []
    plan: List[Dict[str, Any]] = []

    for path in input_files:
        with pdfplumber.open(path) as pdf:
            raw = [p.dedupe_chars().extract_text() or "" for p in pdf.pages]
        compacts = [fold_text(t) for t in raw]

        cover = "\n".join(raw[:2])
        year, quarter = detect_period(path, cover)
        symbol, tax_code = detect_symbol(compacts, cover)
        ranges = locate_ranges(compacts)
        scope = detect_scope(compacts, ranges) if ranges else "unknown"
        lang = detect_lang(compacts, ranges) if ranges else "en"
        form, circular = detect_form_and_circular(raw, ranges)
        unit = detect_unit(raw, ranges)

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
        )
        plan.append(loc.as_dict())

    known = [it.get("symbol") for it in plan if it.get("symbol") and it.get("symbol") != "UNKNOWN"]
    if known:
        fallback = max(set(known), key=known.count)
        for it in plan:
            if it.get("symbol") == "UNKNOWN":
                it["symbol"] = fallback

    return {"extraction_plan": plan, "input_files": input_files}

def select_files(state: FinancialReportState) -> dict:
    """Gom theo kỳ: báo cáo chính dùng bản HỢP NHẤT, bản riêng để đối chiếu."""
    plan = state.get("extraction_plan", []) or []
    grouped: Dict[str, Dict[str, Dict[str, Any]]] = {}

    for item in plan:
        if not item.get("ranges"):
            continue
        key = item.get("period_key") or "UNKNOWN"
        grouped.setdefault(key, {})[item.get("scope", "unknown")] = item

    period_index: List[Dict[str, Any]] = []
    for period_key, scopes in grouped.items():
        preferred = SCOPE_CONSOLIDATED if SCOPE_CONSOLIDATED in scopes else sorted(scopes)[0]
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