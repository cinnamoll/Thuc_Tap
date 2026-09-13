import bisect
import re
from collections import Counter
from dataclasses import dataclass, field as dfield
from typing import Dict, List, Optional, Tuple
import pdfplumber

from Class.NotesExtraction.HeadingBinding import BindingResult, resolve_binding_scoped

ANCHOR_RE = re.compile(r"^[ \t]*(?P<addr>(?:\d+(?:\.\d+)*)|[IVX]+)\.?[ \t]+(?P<title>[A-Z(][^\n]{1,110})$", re.MULTILINE)
ROMAN_RE = re.compile(r"^[IVX]+$")
TRAILING_AMOUNT_RE = re.compile(r"\d[\d.,]{3,}\s*$")   
FORM_NO_RE = re.compile(r"(?im)^[ \t]*Form\s+No\b.*$")
PAGE_NO_RE = re.compile(r"(?m)^[ \t]*\d{1,3}[ \t]*$")
SIGNATURE_RE = re.compile(r"(?is)\b(?:Prepared\s+by|Chief\s+Accountant|General\s+Director|Approved\s+by)\b")

CAPS_HEADING_RE = re.compile(r"^[ \t]*(?P<title>[A-Z][A-Z0-9 ,'\u2019&/()\-.%]{4,79})[ \t]*$", re.MULTILINE)
CAPS_EXCLUDE_RE = re.compile(
    r"(?i)\b(?:notes to|form b|republic|independence|corporation|company|street|"
    r"ward|city|vnd|unit|phone|fax|tax code|address)\b"
)

SECTION_FIELD_RULES: List[Tuple[Tuple[str, ...], str]] = [
    (("balance sheet", "financial position", "bảng cân đối"), "bo_sung_bang_can_doi"),
    (("income statement", "business performance", "profit or loss", "kết quả hoạt động"),
     "bo_sung_ket_qua_kd"),
    (("cash flow", "lưu chuyển tiền tệ"), "bo_sung_luu_chuyen_tien_te"),
    (("other information", "thông tin khác"), "nhung_thong_tin_khac"),
    (("not meet the going", "fails to meet the going", "không đáp ứng giả định"),
     "chinh_sach_khong_lien_tuc"),
    (("accounting policies", "chính sách kế toán"), "chinh_sach_hoat_dong_lien_tuc"),
    (("accounting standard", "accounting regime", "chuẩn mực"), "chuan_muc_che_do"),
    (("accounting period", "currency", "kỳ kế toán", "đơn vị tiền tệ"), "ky_ke_toan_tien_te"),
    (("operational characteristics", "characteristics of", "đặc điểm hoạt động",
      "principal activities", "operating features"), "dac_diem_hoat_dong"),
]

def is_caps_heading(text: str) -> bool:
    s = (text or "").strip()
    if len(s) < 6 or len(s.split()) < 2:
        return False
    if CAPS_EXCLUDE_RE.search(s):
        return False
    letters = [c for c in s if c.isalpha()]
    if len(letters) < 6:
        return False
    if sum(1 for c in letters if c.isupper()) / len(letters) < 0.9:
        return False
    if TRAILING_AMOUNT_RE.search(s):
        return False
    return True

def level_of(addr: Optional[str]) -> int:
    if not addr:
        return 9
    if ROMAN_RE.match(addr):
        return 0
    return addr.count(".") + 1

def is_valid_anchor(match: "re.Match[str]") -> bool:
    addr = match.group("addr")
    title = match.group("title").strip()
    if not addr or len(title) < 3:
        return False
    if len(re.findall(r"[A-Za-z]", title)) < 2:
        return False
    if TRAILING_AMOUNT_RE.search(title):
        return False
    return True

class NoteSpan:
    addr: Optional[str]
    title: str
    level: int
    page_index: int
    text: str
    parent_addr: Optional[str] = None
    parent_idx: Optional[int] = None
    section_idx: Optional[int] = None         
    section_field: Optional[str] = None        
    binding: Optional[BindingResult] = None
    is_section: bool = False

    @property
    def heading(self) -> str:
        """Tiêu đề hiển thị của span: ghép 'addr + title' (dùng làm khoá trong table_metadata)."""
        return f"{self.addr} {self.title}".strip() if self.addr else self.title

    @property
    def composite(self) -> str:
        """Khoá tổ hợp 'parent / addr' để phân biệt các address trùng nhau giữa nhiều section."""
        return f"{self.parent_addr} / {self.addr}" if self.parent_addr else (self.addr or "")

def strip_boilerplate(text: str) -> str:
    text = FORM_NO_RE.sub("", text)
    text = PAGE_NO_RE.sub("", text)
    m = SIGNATURE_RE.search(text)
    if m:
        text = text[: m.start()]
    return text.strip()

SUB_MODEL_FIELDS = {
    "bo_sung_bang_can_doi",
    "bo_sung_ket_qua_kd",
    "bo_sung_luu_chuyen_tien_te",
    "nhung_thong_tin_khac",
}

def leaf_spans(spans: List[NoteSpan]) -> List[NoteSpan]:
    parents = {s.parent_idx for s in spans if s.parent_idx is not None}
    return [s for i, s in enumerate(spans) if i not in parents]

def subtree_text(spans: List[NoteSpan], i: int) -> str:
    parts = [spans[i].text]
    for j, s in enumerate(spans):
        if j == i:
            continue
        k = s.parent_idx
        while k is not None:
            if k == i:
                parts.append(s.text)
                break
            k = spans[k].parent_idx
    return "\n".join(p for p in parts if p)


class NotesOutlineScanner:
    def __init__(self, strip: bool = True):
        self.strip = strip

    @staticmethod
    def load_pages(file_path: str, page_start: int, page_end: int,
                   x_tolerance: int = 30, ocr_fallback: bool = True,
                   ocr_dpi: int = 200, min_chars: int = 40) -> List[str]:
        """Per-page text, falling back to OCR for pages with no text layer.

        A 100% scanned filing (e.g. the SJ1 dataset: 0 chars on all 38 pages)
        yields "" from pdfplumber for every page, so without this fallback the
        scanner used to return nothing at all for scanned input.
        """
        pages: List[str] = []
        with pdfplumber.open(file_path) as pdf:
            for i in range(page_start, page_end + 1):
                pages.append(pdf.pages[i].extract_text(x_tolerance=x_tolerance, layout=True) or "")

        return pages

    def build_spans(self, pages: List[str]) -> List[NoteSpan]:
        """Phân đoạn text notes thành các NoteSpan theo outline.
        Thuật toán: (1) thu 2 loại anchor — có đánh số (ANCHOR_RE) và tiêu đề IN HOA không số;
        (2) loại dòng lặp >=3 lần hoặc nằm trong header lặp (page furniture);
        (3) base_level = mức nông nhất có >=2 anchor;
        (4) span mỗi anchor kéo dài tới anchor kế tiếp có level <= level của nó;
        parent-stack lưu tổ tiên để suy ra section chứa span (is_section, section_idx).
        """
        parts, offsets, off = [], [], 0
        for t in pages:
            offsets.append(off)
            parts.append(t)
            off += len(t) + 1
        full = "\n".join(parts)

        anchors = [(m.start(), m.end(), m.group("addr"), m.group("title").strip())
                   for m in ANCHOR_RE.finditer(full) if is_valid_anchor(m)]
        # unnumbered ALL-CAPS headings act as the level-0 sections
        anchors += [(m.start(), m.end(), None, m.group("title").strip())
                    for m in CAPS_HEADING_RE.finditer(full)
                    if is_caps_heading(m.group("title"))]
        anchors.sort(key=lambda t: t[0])

        # Repeated page furniture (headers/footers) is not a heading: the SJ1
        # scan repeats "HUNG HAU" on every page, which used to become a bogus
        # level-0 section and mis-scope the whole document.
        def _norm(text: str) -> str:
            """Chuẩn hoá nội dung một dòng (gộp khoảng trắng + uppercase) để đếm tần suất dòng lặp.
            """
            return re.sub(r"\s+", " ", text or "").strip().upper()

        counts = Counter(_norm(a[3]) for a in anchors)
        anchors = [a for a in anchors if counts[_norm(a[3])] <= 2]

        # ...and a caps "heading" that is just a fragment of a repeated header
        # (SJ1 repeats "HUNG HAU AGRICULTURAL CORPORATION ..." on every page, and
        # some pages split it so the bare "HUNG HAU" line survives the filter).
        line_counts = Counter(_norm(ln) for ln in full.splitlines() if ln.strip())
        repeated = [ln for ln, n in line_counts.items() if n >= 3 and len(ln) >= 6]
        anchors = [a for a in anchors
                   if not (a[2] is None and any(_norm(a[3]) in ln for ln in repeated))]

        levels = [0 if a[2] is None else level_of(a[2]) for a in anchors]
        level_counts = Counter(levels)
        # base_level = shallowest level that actually looks like a level (>=2
        # anchors), so a single stray shallow line cannot flatten the outline.
        multi = [lv for lv, n in level_counts.items() if n >= 2]
        base_level = min(multi) if multi else (min(levels) if levels else 0)

        spans: List[NoteSpan] = []
        stack: List[Tuple[int, str, int]] = []
        for i, (start, stop, addr, title) in enumerate(anchors):
            lv = levels[i]
            while stack and stack[-1][0] >= lv:
                stack.pop()
            end = len(full)
            for j in range(i + 1, len(anchors)):
                if levels[j] <= lv:
                    end = anchors[j][0]
                    break
            parent = stack[-1] if stack else None
            stack.append((lv, addr or title, i))
            body = full[stop:end]
            spans.append(NoteSpan(
                addr=addr, title=title, level=lv,
                page_index=max(0, bisect.bisect_right(offsets, start) - 1),
                text=strip_boilerplate(body) if self.strip else body.strip(),
                parent_addr=parent[1] if parent else None,
                parent_idx=parent[2] if parent else None,
                is_section=(lv == base_level),
            ))

        for i, s in enumerate(spans):
            j = i if s.is_section else s.parent_idx
            while j is not None and not spans[j].is_section:
                j = spans[j].parent_idx
            s.section_idx = j
        return spans

    def route(self, spans: List[NoteSpan]) -> List[NoteSpan]:
        for s in spans:
            if s.is_section:
                h = s.title.lower()
                for keys, field in SECTION_FIELD_RULES:
                    if any(k in h for k in keys):
                        s.section_field = field
                continue
            sec = spans[s.section_idx] if s.section_idx is not None else None
            if sec is not None and sec.section_field in SUB_MODEL_FIELDS:
                s.section_field = sec.section_field
                s.binding = resolve_binding_scoped(
                    s.heading, section_field=sec.section_field, addr=s.addr)
        return spans

    def to_segments(self, spans: List[NoteSpan]) -> Dict[str, Dict[str, str]]:
        out: Dict[str, Dict[str, str]] = {}
        leaves = set(id(s) for s in leaf_spans(spans))
        for i, s in enumerate(spans):
            if s.is_section:
                if s.section_field and s.section_field not in SUB_MODEL_FIELDS:
                    out.setdefault(s.section_field, {})["text"] = subtree_text(spans, i)
                continue
            if id(s) not in leaves or not s.section_field:
                continue
            key = s.binding.sub_key if s.binding else "thong_tin_khac"
            bucket = out.setdefault(s.section_field, {})
            bucket[key] = (bucket.get(key, "") + s.text + "\n").strip()
        return out

    def scan(self, file_path: str, page_start: int, page_end: int, **load_kwargs) -> List[NoteSpan]:
        pages = self.load_pages(file_path, page_start, page_end, **load_kwargs)
        return self.route(self.build_spans(pages))