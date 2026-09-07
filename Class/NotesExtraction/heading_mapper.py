import re

class HeadingMapper:
    SECTION_NO = re.compile(r"^(?:(\d{1,2}(?:\.\d+)?)[\s.]*)?([A-Za-zÀ-ỹ][\w ,'’&/()-]{2,80})$")
    NUMBER_FORMAT = re.compile(r"^\d{1,2}(\.\d+)?$")
    SECTION_HEADER_RE = re.compile(r"^(?:(\d{1,2}(?:\.\d+)?)[\s.]*)?([A-Za-zÀ-ỹ][\w ,'’&/()-]{2,80})$", re.MULTILINE)
    
    HEADING_TO_SECTION: list[tuple[list[str], str]] = [
        (["cash", "receivable", "inventory", "inventories", "tangible", "intangible", "fixed asset", "investment","payable", "loan", "borrowing", "finance lease", "provision", "equity", "prepaid"],
            "bo_sung_bang_can_doi",
        ),
        (["revenue", "income", "expense", "cost of", "profit","selling", "administrative", "financial income", "financial expense"],
            "bo_sung_ket_qua_kd",
        ),
        (["cash flow", "operating activities","investing activities", "financing activities"],
            "bo_sung_luu_chuyen_tien_te",
        ),
        (["contingent", "commitment", "related part", "segment", "subsequent", "event after", "going concern", "comparative",],
            "nhung_thong_tin_khac",
        ),
    ]

    HEADER_NOISE = ("corporation", "company limited", "financial statements",
                    "notes to the", "form b", "prepared by", "chief accountant",
                    "general director", "approved by", "circular no.",
                    "ministry of finance", "agricultural corporation")

    _TITLE_STOPWORDS = {"current", "previous", "period", "amount", "as", "at",
                        "dec", "oct", "jan", "feb", "sep", "unit", "vnd",
                        "balance", "opening", "closing", "beginning", "ending",
                        "cost", "book", "value", "depreciation", "historical",
                        "net", "allocated", "accumulated", "the", "of", "for"}

    @classmethod
    def map_heading_to_section(cls, heading: str) -> str:
        h = heading.lower()
        for keywords, section_key in cls.HEADING_TO_SECTION:
            if any(kw in h for kw in keywords):
                return section_key
        return "bo_sung_bang_can_doi"

    @classmethod
    def _clean_heading(cls, text: str) -> str:
        if not text:
            return ""
        t = re.sub(r"\s+", " ", text).strip()
        t = cls._strip_column_headers(t)
        if not t or len(t) > 90:
            return ""
        low = t.lower()
        if any(n in low for n in cls.HEADER_NOISE):
            return ""
        m = re.match(r"^(?:(\d{1,2}(?:\.\d+)?)[\s.]*)?([A-Za-zÀ-ỹ][\w ,'’&()/-]*)$", t)
        if not m:
            return ""
        title = m.group(2).strip()
        if not title or not re.search(r"[A-Za-zÀ-ỹ]{2,}", title):
            return ""
        if re.search(r"\d{1,3}(?:[.,]\d{3})+", title):
            return ""
        if re.match(r"^(?:As at|Current period|Previous period|Amount|Book value|"
                    r"Historical cost|Net book value|Allocated amount|Accumulated "
                    r"depreciation|Total|Opening|Closing|Beginning|Ending|Cost|"
                    r"Unit|VND)[ .:,]*(?:Period|balance)?$", title, re.I):
            return ""
        if re.match(r"^(?:As at\s+)?(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)"
                    r"[a-z]*\.?\s+\d{1,2}[,.]?\s+\d{2,4}$", title, re.I):
            return ""
        return t

    @classmethod
    def _strip_column_headers(cls, text: str) -> str:
        if not text:
            return ""
        tokens = text.split()
        cut = len(tokens)
        for i, tok in enumerate(tokens):
            if i >= 2 and re.fullmatch(r"(?:Dec|Oct|Jan|Sep|Current|Previous)\.?,?", tok, re.I):
                cut = i
                break
        return " ".join(tokens[:cut]).strip()

    @classmethod
    def parse_section_key(cls, heading: str):
        if not heading or not isinstance(heading, str):
            return (999, 0)
        m = re.match(r"^(\d{1,2})(?:\.(\d{1,2}))?\s", heading)
        if not m:
            return (999, 0)
        return (int(m.group(1)), int(m.group(2)) if m.group(2) else 0)

    @classmethod
    def is_valid_section_key(cls, heading: str) -> bool:
        if not heading or not isinstance(heading, str):
            return False
        t = heading.strip()
        if not t or len(t) > 80:
            return False
        if re.match(r"^Table_p\d", t, re.I):
            return False
        low = t.lower()
        if any(n in low for n in cls.HEADER_NOISE):
            return False
        if not re.search(r"[A-Za-zÀ-ỹ]{2,}", t):
            return False
        return cls._clean_heading(t) == t

    @classmethod
    def _heading_from_rows(cls, rows):
        NUMBERED = re.compile(r"^(\d{1,2}(?:\.\d+)?)$")
        for r in rows:
            text = " ".join(w.text for w in r).strip()
            text_clean = cls._clean_heading(text)
            if text_clean:
                return text_clean

        for idx, r in enumerate(rows):
            text = " ".join(w.text for w in r).strip()
            m = NUMBERED.match(text)
            if m and idx + 1 < len(rows):
                next_text = " ".join(w.text for w in rows[idx + 1]).strip()
                if re.search(r"[A-Za-zÀ-ỹ]{3,}", next_text):
                    text_combined = f"{text} {next_text}"
                    text_clean = cls._clean_heading(text_combined)
                    if text_clean:
                        return text_clean
        return ""

    @classmethod
    def heading_above(cls, block, visual_rows):
        top = block.get("top")
        if top is None and block.get("rows"):
            top = block["rows"][0][0].top
        if top is None:
            return ""
        above = [r for r in visual_rows if r[0].bottom <= top]
        above.sort(key=lambda r: (r[0].top, r[0].x0))
        candidates = []
        for r in reversed(above):
            if candidates:
                gap = candidates[-1][0].top - r[-1].bottom
                if gap > 45.0:
                    break
            candidates.append(r)
        candidates.reverse()
        for r in reversed(candidates):
            text = " ".join(w.text for w in r).strip()
            text_clean = cls._clean_heading(text)
            if text_clean:
                return text_clean
        return ""

    @classmethod
    def _title_above(cls, block, visual_rows, is_amount_token_func) -> str:
        top = block.get("top")
        if top is None and block.get("rows"):
            top = block["rows"][0][0].top
        if top is None:
            return ""
        best = ""
        for r in reversed(visual_rows):
            if not r:
                continue
            if r[0].bottom > top + 2.0:
                continue
            if any(is_amount_token_func(w.text) for w in r):
                continue
            text = " ".join(w.text for w in r).strip()
            cleaned = cls._clean_heading(text)
            if not cleaned or len(cleaned) > 60:
                continue
            tokens = {tk.lower().rstrip(".,") for tk in cleaned.split()}
            if any(tk not in cls._TITLE_STOPWORDS for tk in tokens):
                best = cleaned
                break
        return best