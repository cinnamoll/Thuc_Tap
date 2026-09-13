import re

from Class.NotesExtraction.HeadingBinding import resolve_binding

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
        )
    ]

    HEADER_NOISE = ("corporation", "company limited", "financial statements", "notes to the", "form b", "prepared by", "chief accountant",
                    "general director", "approved by", "circular no.", "ministry of finance", "agricultural corporation")

    SUB_KEY_PATTERNS: list[tuple[str, str]] = [
        (r"\b(vay và nợ|vay và nợ thuê|borrowing|borrowings|loan|loans)\b", "vay_va_no_thue_tai_chinh"),
        (r"\b(tài sản cố định thuê tài chính|tài sản thuê tài chính|finance lease asset)\b", "tang_giam_tscd_thue_tai_chinh"),
        (r"\b(cash|tiền|tương đương tiền)\b", "tien"),
        (r"\b(đầu tư tài chính|financial investment|investment)\b", "dau_tu_tai_chinh"),
        (r"\b(phải thu khách hàng|trade receivable|receivables from customer)\b", "phai_thu_khach_hang"),
        (r"\b(trả trước người bán|prepayment to supplier|advance to supplier)\b", "tra_truoc_nguoi_ban"),
        (r"\b(tài sản thiếu|shortage)\b", "tai_san_thieu_cho_xu_ly"),
        (r"\b(nợ xấu|bad debt|doubtful debt)\b", "no_xau"),
        (r"\b(hàng tồn kho|inventory|inventories)\b", "hang_ton_kho"),
        (r"\b(tài sản cố định hữu hình|tangible fixed asset|tangible fixed assets)\b", "tang_giam_tscd_huu_hinh"),
        (r"\b(tài sản cố định vô hình|intangible fixed asset|intangible fixed assets)\b", "tang_giam_tscd_vo_hinh"),
        (r"\b(bất động sản đầu tư|investment property|investment properties)\b", "bat_dong_san_dau_tu"),
        (r"\b(dở dang dài hạn|construction in progress|work in progress)\b", "tai_san_do_dang_dai_han"),
        (r"\b(chi phí trả trước|prepaid expense|prepaid expenses)\b", "chi_phi_tra_truoc"),
        (r"\b(phải trả người bán|trade payable|trade payables|payables to supplier)\b", "phai_tra_nguoi_ban"),
        (r"\b(người mua trả tiền trước|advance from customer|advances from customer)\b", "nguoi_mua_tra_tien_truoc"),
        (r"\b(thuế và các khoản|tax|statutory|thuế)\b", "thue_va_cac_khoan_nop_nha_nuoc"),
        (r"\b(chi phí phải trả|accrued expense|accrued expenses)\b", "chi_phi_phai_tra"),
        (r"\b(doanh thu chưa thực hiện|unearned revenue|deferred revenue)\b", "doanh_thu_chua_thuc_hien"),
        (r"\b(trái phiếu phát hành|bond|bonds|bond issuance)\b", "trai_phieu_phat_hanh"),
        (r"\b(dự phòng phải trả|provision|provisions)\b", "du_phong_phai_tra"),
        (r"\b(vốn chủ sở hữu|owner|owners|equity|share capital)\b", "von_chu_so_huu"),
        (r"\b(nguồn kinh phí|fund|funding)\b", "nguon_kinh_phi"),
        (r"\b(ngoại bảng|off-balance)\b", "cac_khoan_muc_ngoai_bang"),
        (r"\b(phải thu khác|other receivable|other receivables)\b", "phai_thu_khac"),
        (r"\b(phải trả khác|other payable|other payables)\b", "phai_tra_khac"),
        (r"\b(giảm trừ doanh thu|revenue deduction|revenue deductions)\b", "giam_tru_doanh_thu"),
        (r"\b(doanh thu bán hàng|tổng doanh thu|gross revenue|net revenue|revenue)\b", "tong_doanh_thu"),
        (r"\b(giá vốn hàng bán|cost of sales|cost of goods sold)\b", "gia_von_hang_ban"),
        (r"\b(doanh thu tài chính|financial income|finance income)\b", "doanh_thu_tai_chinh"),
        (r"\b(chi phí tài chính|financial expense|finance cost|finance costs)\b", "chi_phi_tai_chinh"),
        (r"\b(chi phí bán hàng|chi phí quản lý|selling expense|general and administrative|g&a)\b", "chi_phi_ban_hang_va_qldn"),
        (r"\b(theo yếu tố|by element|operating cost by element)\b", "chi_phi_sxkd_theo_yeu_to"),
        (r"\b(thu nhập khác|other income)\b", "thu_nhap_khac"),
        (r"\b(chi phí khác|other expense|other expenses)\b", "chi_phi_khac"),
        (r"\b(thuế tndn hoãn lại|deferred tax|deferred income tax)\b", "chi_phi_thue_tndn_hoan_lai"),
        (r"\b(thuế tndn|corporate income tax|cit expense)\b", "chi_phi_thue_tndn_hien_hanh"),
        (r"\b(không bằng tiền|non-cash)\b", "giao_dich_khong_bang_tien"),
        (r"\b(không được sử dụng|restricted cash)\b", "tien_khong_duoc_su_dung"),
        (r"\b(đi vay thực thu|proceeds from borrowing)\b", "tien_di_vay_thuc_thu"),
        (r"\b(trả gốc vay|repayment of borrowing)\b", "tien_da_tra_goc_vay"),
        (r"\b(nợ tiềm tàng|cam kết|contingent|commitment|commitments)\b", "no_tiem_tang_cam_ket"),
        (r"\b(sự kiện sau|subsequent event|event after)\b", "su_kien_sau_ngay_ket_thuc"),
        (r"\b(bên liên quan|related party|related parties)\b", "thong_tin_ben_lien_quan"),
        (r"\b(báo cáo bộ phận|segment|segments)\b", "bao_cao_bo_phan"),
        (r"\b(hoạt động liên tục|going concern)\b", "thong_tin_hoat_dong_lien_tuc"),
        (r"\b(thông tin so sánh|comparative)\b", "thong_tin_so_sanh"),
    ]
    TITLE_STOPWORDS = {"current", "previous", "period", "amount", "as", "at", "dec", "oct", "jan", "feb", "sep", "unit", "vnd",
                        "balance", "opening", "closing", "beginning", "ending", "cost", "book", "value", "depreciation", "historical",
                        "net", "allocated", "accumulated", "the", "of", "for"}

    @classmethod
    def map_heading_to_section(cls, heading: str) -> str:
        return resolve_binding(heading).field

    @classmethod
    def map_heading_to_sub_key(cls, heading: str) -> str:
        return resolve_binding(heading).sub_key

    @classmethod
    def clean_heading(cls, text: str) -> str:
        if not text:
            return ""
        t = text.strip()
        t = re.sub(r'^[“"\'‘`«„\-_—~•\s]+', '', t)
        t = re.sub(r"\s+", " ", t).strip()
        
        tokens = t.split()
        cut = len(tokens)
        for i, tok in enumerate(tokens):
            if i >= 2 and re.fullmatch(r"(?:Dec|Oct|Jan|Sep|Current|Previous)\.?,?", tok, re.I):
                cut = i
                break
        t =  " ".join(tokens[:cut]).strip()
        
        if not t or len(t) > 90 or len(t) < 3:
            return ""
        low = t.lower()
        if any(n in low for n in cls.HEADER_NOISE):
            return ""
        if re.match(r"^(?:or|and|of|the|in|on|at|to|by|for|from|with|as)\b", low):
            return ""
        if not re.match(r"^(?:(?:\d{1,2}(?:\.[0-9a-zA-Z]+)*|[a-z]\.)[\s.]*)?[A-Za-zÀ-Ỹ]", t):
            return ""
        if re.match(r"^[12]\.", t):
            return ""

        m = re.match(r"^(?:(?:\d{1,2}(?:\.[0-9a-zA-Z]+)*|[a-z]\.)[\s.]*)?([A-Za-zÀ-ỹ][\w ,'’&()/-]*)$", t)
        if not m:
            return ""
        title = m.group(1).strip()
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
        return cls.clean_heading(t) == t

    @classmethod
    def heading_from_rows(cls, rows):
        NUMBERED = re.compile(r"^(\d{1,2}(?:\.[0-9a-zA-Z]+)?)$")
        for r in rows:
            text = " ".join(w.text for w in r).strip()
            text_clean = cls.clean_heading(text)
            if text_clean and (re.match(r"^\d", text_clean) or len(text_clean.split()) >= 2):
                return text_clean

        for idx, r in enumerate(rows):
            text = " ".join(w.text for w in r).strip()
            m = NUMBERED.match(text)
            if m and idx + 1 < len(rows):
                next_text = " ".join(w.text for w in rows[idx + 1]).strip()
                if re.search(r"[A-Za-zÀ-ỹ]{3,}", next_text):
                    text_combined = f"{text} {next_text}"
                    text_clean = cls.clean_heading(text_combined)
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
            row_txt = " ".join(w.text for w in r).strip()
            if re.search(r"\b(?:Total|Unit:\s*VND)\b", row_txt, re.I):
                break
            if len(re.findall(r"\b\d{1,3}(?:,\d{3})+\b", row_txt)) >= 2:
                break
            candidates.append(r)
        candidates.reverse()
        
        for r in reversed(candidates):
            text = " ".join(w.text for w in r).strip()
            if re.match(r"^\d{1,2}(?:\.[0-9a-zA-Z]+)?\s+[A-Z]", text):
                text_clean = cls.clean_heading(text)
                if text_clean:
                    return text_clean
                    
        for r in reversed(candidates):
            text = " ".join(w.text for w in r).strip()
            text_clean = cls.clean_heading(text)
            if text_clean and (re.match(r"^\d", text_clean) or len(text_clean.split()) >= 2):
                return text_clean
        return ""

    @classmethod
    def title_above(cls, block, visual_rows, is_amount_token_func) -> str:
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
            cleaned = cls.clean_heading(text)
            if not cleaned or len(cleaned) > 60:
                continue
            tokens = {tk.lower().rstrip(".,") for tk in cleaned.split()}
            if any(tk not in cls.TITLE_STOPWORDS for tk in tokens):
                best = cleaned
                break
        return best