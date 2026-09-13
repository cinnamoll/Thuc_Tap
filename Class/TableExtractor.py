import re
import unicodedata
from typing import Optional, Dict, List
import pdfplumber

from parse_financial_number import parse_number

from Class.ReportContent.BalanceSheet import BalanceSheet, BalanceSheetLine
from Class.ReportContent.IncomeStatement import IncomeStatement, IncomeStatementLine
from Class.ReportContent.CashFlowStatement import CashFlowStatement, CashFlowLine

RE_FINANCIAL = re.compile(r"^\(?\d[\d,. ]{2,}\d\)?$")
RE_CODE = re.compile(r"^\(?(\d{2,3}[a-zA-Z]?)\)?$")
RE_SHORT_NUM = re.compile(r"^[(]?\d{1,3}[a-zA-Z]?[)]?$")
PREFIX_PATTERN = re.compile(r"^\s*(?:(?:\d+\s+)?([A-E]|[IVXLCDM]+|\d+))[\.\-\–\—\:]\s*")
SECTION_PREFIX_RE = re.compile(r"^\s*([A-E]|[IVXLCDM]+)[\.\-\–\—\s]")
FOOTER_KW = ["chief accountant", "general director", "prepared by", "director","người lập", "kế toán trưởng", "giám đốc", "tổng giám đốc"]

BS_NUM_FIELDS = ("so_cuoi_ky", "so_dau_nam")
PL_NUM_FIELDS = ("ky_nay", "ky_truoc", "luy_ke_ky_nay", "luy_ke_ky_truoc")
CF_NUM_FIELDS = ("luy_ke_ky_nay", "luy_ke_ky_truoc")

NUM_TOKEN_RE = re.compile(r"[-(]?\d[\d.,]*\)?")
FIN_NUM_RE = re.compile(r"(?:-|\()?\d{1,3}(?:,\d{3})+(?:\))?")
YEAR_RE = re.compile(r"^(?:19|20)\d{2}$")
DOUBLED_PUNCT_RE = re.compile(r"([,.\-()])\1+")

def fold_text(text: str) -> str:
    text = (text or "").replace("đ", "d").replace("Đ", "d")
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]", "", text.lower())

def folded_contains(folded: str, keyword: str) -> bool:
    pattern = "".join(re.escape(c) + "+" for c in keyword)
    return re.search(pattern, folded) is not None

# Thứ tự QUAN TRỌNG:
#  - "revenuefromfinancial" phải đứng trước "revenuefrom" (DTTC vs doanh thu).
#  - "profitafter" phải đứng trước "corporateincometax" (dòng 60 có cả hai cụm).
#  - "doanh_thu" để CUỐI CÙNG.
# Từ khoá cố ý dùng tiền tố ngắn vì nhãn biến thể giữa các template
#   ("Revenue from financial operations" / "... activities").
PL_LABEL_RULES = [
    ("cac_khoan_giam_tru", ("revenuededuction", "cackhoangiamtru")),
    ("doanh_thu_thuan", ("netrevenue", "doanhthuthuan")),
    ("gia_von_hang_ban", ("goodssold", "giavonhangban")),
    ("loi_nhuan_gop", ("grossprofit", "loinhuangop")),
    ("doanh_thu_tai_chinh", ("revenuefromfinancial", "doanhthuhoatdongtaichinh")),
    ("chi_phi_tai_chinh", ("financialexpense", "chiphitaichinh")),
    ("chi_phi_ban_hang", ("sellingexpense", "chiphibanhang")),
    ("chi_phi_quan_ly", ("generalandadmini", "generaladmini", "chiphiquanly")),
    ("loi_nhuan_thuan_kd", ("netprofitfrom", "loinhuanthuantu")),
    ("loi_nhuan_truoc_thue", ("profitbeforetax", "loinhuantruocthue")),
    ("loi_nhuan_sau_thue", ("profitafter", "loinhuansauthue")),
    ("chi_phi_thue_tndn", ("corporateincometax", "chiphithuetndn")),
    ("doanh_thu", ("revenuefrom", "doanhthubanhang")),
]

# Fallback theo mã số cho các chỉ tiêu có CÙNG mã ở cả TT 200/2014 và TT 99/2025.
PL_CODE_FALLBACK = {
    "01": "doanh_thu",
    "10": "doanh_thu_thuan",
    "11": "gia_von_hang_ban",
    "20": "loi_nhuan_gop",
    "30": "loi_nhuan_thuan_kd",
    "50": "loi_nhuan_truoc_thue",
    "60": "loi_nhuan_sau_thue",
}


def match_pl_field(label: str, code: Optional[str] = None) -> Optional[str]:
    """Suy ra field chỉ tiêu của Báo cáo KQKD từ NHÃN (ưu tiên) rồi tới MÃ SỐ.

    Không dựa duy nhất vào mã số vì TT 200/2014 và TT 99/2025 đánh số khác nhau
    (ví dụ mã 21: TT200 = doanh thu tài chính, TT99/2025 = lãi thanh lý BĐS đầu tư).
    """
    label = (label or "").replace("đ", "d").replace("Đ", "d")
    label = unicodedata.normalize("NFD", label)
    label = "".join(c for c in label if unicodedata.category(c) != "Mn")
    folded = re.sub(r"[^a-z0-9]", "", label.lower())
    if folded:
        for field, keywords in PL_LABEL_RULES:
            for kw in keywords:
                if folded_contains(folded, kw):
                    return field
    return PL_CODE_FALLBACK.get(code) if code else None

class Word:
    def __init__(self, text: str, x0: float, x1: float, top: float, bottom: float):
        self.text = text
        self.x0 = x0
        self.x1 = x1
        self.top = top
        self.bottom = bottom

class Row:
    def __init__(self, y_center: float):
        self.y_center = y_center
        self.words: list[Word] = []
        self.cells: dict[str, str] = {}

def coerce_financial(value):
    """Best-effort numeric coercion for OCR-noisy cells -> (number|None, warn|None).

    Handles the four shapes seen in the SJ1 scan:
        clean value                          -> unchanged
        two numbers merged in one cell       -> first number + warning
        value plus a stray glyph (7A.)       -> first number + warning
        label prefix (S 7,002,880,618)       -> the number + warning
    """
    if value is None:
        return None, None
    text = str(value).strip()
    if not text or text in ("-", "\u2014", "\u2013"):
        return None, None

    # TT 99/2025 render dấu trừ thành token tách rời: "- 1,234,567" hoặc "1,234,567 -".
    # Gộp lại thành số âm trước khi parse (nếu không sẽ mất dấu và sai đẳng thức).
    compact = re.sub(r"\s+", "", text)
    if compact != text:
        if compact.startswith("-") and len(compact) > 1:
            text = "-" + compact.lstrip("-")
        elif compact.endswith("-") and len(compact) > 1:
            text = "-" + compact.rstrip("-")
        else:
            text = compact

    tokens = NUM_TOKEN_RE.findall(text)
    if len(tokens) >= 2:
        num = parse_number(tokens[0])
        if isinstance(num, (int, float)):
            return num, f"multi-value cell {text!r} -> {tokens[0]!r}"

    single = parse_number(text)
    if isinstance(single, (int, float)):
        return single, None

    if tokens:
        num = parse_number(tokens[0])
        if isinstance(num, (int, float)):
            return num, f"recovered {tokens[0]!r} from {text!r}"
    return None, f"unparseable value dropped: {text!r}"

class TableExtractor:
    """Bộ trích bảng số liệu chính của BCTC (Bảng cân đối / KQKD / Lưu chuyển tiền tệ).
    Luồng: words (pdfplumber, fallback OCR) -> gom dòng -> suy biên cột -> gán ô ->
    làm sạch/chuẩn hoá -> dict -> dựng model theo mã số.
    Các giá trị số được làm sạch nhiễu OCR (coerce_financial) và mỗi dòng được bọc try/except
    để một ô lỗi không làm hỏng cả báo cáo.
    """
    def __init__(self):
        self.dpi = 300
        self.warnings: list[str] = []
        self.RE_FINANCIAL = RE_FINANCIAL
        self.RE_CODE = RE_CODE
        self.RE_NOTES_NUM = re.compile(r"^\d{1,2}$")
        self.RE_SHORT_NUM = RE_SHORT_NUM
        self.FOOTER_KW = FOOTER_KW

    def is_financial_number(self, text: str) -> bool:
        t = text.strip()
        if any(c in t for c in ["=", "+", "®", "©"]):
            return False
        if "/" in t or re.search(r"\d-\d", t):
            return False
        # Loại "năm trần" (2024/2025/2026): chúng không phải số liệu tài chính
        # nhưng nếu tính vào sẽ kéo min_fin_x0 sang trái và làm đứt band `code`.
        if YEAR_RE.match(t):
            return False
        digit_only = re.sub(r"[,.()\- ]", "", t)
        if not digit_only.isdigit():
            return False
        if len(digit_only) >= 4:
            return bool(self.RE_FINANCIAL.match(t)) or ("," in t or "." in t)
        return False

    def cluster_positions(self, positions: list[float], gap: float) -> list[tuple[float, float]]:
        """Gom các toạ độ đã sort thành cụm liên tiếp khi khoảng cách <= gap; trả (min, max) mỗi cụm —
        dùng để phát hiện biên cột trên trang.
        """
        if not positions:
            return []
        positions = sorted(positions)
        clusters = []
        current_cluster = [positions[0]]
        for p in positions[1:]:
            if p - current_cluster[-1] <= gap:
                current_cluster.append(p)
            else:
                clusters.append((min(current_cluster), max(current_cluster)))
                current_cluster = [p]
        if current_cluster:
            clusters.append((min(current_cluster), max(current_cluster)))
        return clusters

    def group_into_lines(self, words: list[Word]) -> list[list[Word]]:
        """Gom Word thành dòng theo trục dọc: chèn vào dòng hiện tại khi vùng bao chồng lấn >40%
        hoặc tâm lệch <5pt; mỗi dòng sort theo x0 để giữ thứ tự đọc trái sang phải.
        """
        if not words:
            return []
        sorted_words = sorted(words, key=lambda w: (w.top + w.bottom) / 2)
        lines: list[list[Word]] = []
        current_line = [sorted_words[0]]
        for w in sorted_words[1:]:
            line_top = min(x.top for x in current_line)
            line_bottom = max(x.bottom for x in current_line)
            overlap = min(w.bottom, line_bottom) - max(w.top, line_top)
            h_w = w.bottom - w.top
            h_line = line_bottom - line_top
            min_h = min(h_w, h_line)
            if overlap > 0.4 * min_h or abs(((w.top + w.bottom) / 2) - ((line_top + line_bottom) / 2)) < 5.0:
                current_line.append(w)
            else:
                current_line.sort(key=lambda x: x.x0)
                lines.append(current_line)
                current_line = [w]
        if current_line:
            current_line.sort(key=lambda x: x.x0)
            lines.append(current_line)
        return lines

    def infer_bands_from_data(self, data_lines: list[list[Word]], page_width: float, report_type: str = "BS", 
                              expected_num_cols: Optional[int] = None) -> list[tuple[str, float, float]]:
        """Suy ra biên các cột của bảng: (1) lấy các word số có x0 >= 0.35 bề rộng trang;
        (2) cluster theo x1 để tìm biên phải từng cột số; (3) giới hạn theo số cột kỳ vọng
        (BS/CF = 2, PL = 2 hoặc 4); (4) dò dòng header để tách thêm band code/notes;
        (5) trả list (tên band, start, end) đã chuẩn hoá về 0..1.
        """
        fin_words = []
        for line in data_lines:
            for w in line:
                if w.x0 >= 0.35 * page_width and self.is_financial_number(w.text):
                    fin_words.append(w)
        if not fin_words:
            return []

        min_fin_x0 = min(w.x0 for w in fin_words)
        gap_pt = page_width * 0.03
        x1_clusters = self.cluster_positions([w.x1 for w in fin_words], gap_pt)
        x1_clusters = [c for c in x1_clusters if sum(1 for w in fin_words if c[0] <= w.x1 <= c[1]) >= 2 or len(x1_clusters) <= 2]

        num_bands_raw = []
        for lo, hi in x1_clusters:
            cluster_words = [w for w in fin_words if lo - gap_pt <= w.x1 <= hi + gap_pt]
            col_x0 = min(w.x0 for w in cluster_words) if cluster_words else lo - gap_pt
            num_bands_raw.append((col_x0, hi))

        if expected_num_cols is None:
            if report_type in ("BS", "CF"):
                expected_num_cols = 2
            elif report_type == "PL":
                expected_num_cols = 4 if len(num_bands_raw) >= 4 else 2
            else:
                expected_num_cols = len(num_bands_raw)

        if len(num_bands_raw) > expected_num_cols:
            num_bands_raw = num_bands_raw[-expected_num_cols:]

        num_bands = []
        for idx, (x0, x1) in enumerate(num_bands_raw):
            band_start = min_fin_x0 if idx == 0 else (num_bands_raw[idx - 1][1] + x0) / 2
            band_end = page_width if idx == len(num_bands_raw) - 1 else (x1 + num_bands_raw[idx + 1][0]) / 2
            num_bands.append((band_start / page_width, band_end / page_width))

        code_header = None
        notes_header = None
        # KHÔNG ràng buộc `w.x1 < min_fin_x0`: số căn phải nhiều chữ số có thể kéo x0
        # sang trái và chồng lên vùng cột code, nếu ràng buộc sẽ mất luôn band code.
        for line in data_lines[:6]:
            for w in line:
                t = w.text.strip().lower()
                if t in ("code", "mã số", "mã") and 0.15 * page_width <= w.x0 < 0.60 * page_width:
                    code_header = w
                elif t in ("note", "notes", "thuyết minh") and 0.15 * page_width <= w.x0 < 0.75 * page_width:
                    notes_header = w

        code_band = None
        notes_band = None
        if code_header and notes_header:
            code_band = (max(0.18, (code_header.x0 - gap_pt) / page_width), (notes_header.x0 - gap_pt / 2) / page_width)
            notes_band = (code_band[1], min_fin_x0 / page_width)
        elif code_header:
            code_band = (max(0.18, (code_header.x0 - gap_pt) / page_width), min_fin_x0 / page_width)
        else:
            code_candidates = []
            for line in data_lines:
                for w in line:
                    if 0.18 * page_width <= w.x0 and w.x1 < min_fin_x0:
                        t = w.text.strip()
                        if any(c in t for c in ["=", "+", "-", "*", "/", "%"]):
                            continue
                        clean_t = t.strip("()")
                        if RE_CODE.match(clean_t):
                            code_candidates.append(w)
            if code_candidates:
                cand_clusters = self.cluster_positions([w.x1 for w in code_candidates], gap_pt)
                cand_clusters = [c for c in cand_clusters if c[1] < min_fin_x0]
                cand_clusters.sort(key=lambda c: c[0])
                if len(cand_clusters) >= 2:
                    c0, c1 = cand_clusters[-2:]
                    code_band = (max(0.18, (c0[0] - gap_pt) / page_width), min(c0[1] + gap_pt, c1[0]) / page_width)
                    notes_band = (code_band[1], min_fin_x0 / page_width)
                elif len(cand_clusters) == 1:
                    c0 = cand_clusters[0]
                    code_band = (max(0.18, (c0[0] - gap_pt) / page_width), min_fin_x0 / page_width)

        if code_band and num_bands:
            # Kẹp band số đầu tiên bắt đầu SAU band code, tránh mã số lọt vào cột số.
            first_start, first_end = num_bands[0]
            if first_start < code_band[1] < first_end:
                num_bands[0] = (code_band[1], first_end)

        bands = []
        items_end = code_band[0] if code_band else num_bands[0][0]
        bands.append(("items", 0.0, items_end))
        if code_band:
            bands.append(("code", code_band[0], code_band[1]))
        if notes_band and notes_band[1] > notes_band[0]:
            bands.append(("notes", notes_band[0], notes_band[1]))

        if report_type == "BS":
            cnames = ["so_cuoi_ky", "so_dau_nam"]
        elif report_type == "CF":
            cnames = ["luy_ke_ky_nay", "luy_ke_ky_truoc"]
        elif report_type == "PL":
            if len(num_bands) >= 4:
                cnames = ["ky_nay", "ky_truoc", "luy_ke_ky_nay", "luy_ke_ky_truoc"]
            else:
                cnames = ["ky_nay", "ky_truoc"]
        else:
            cnames = [f"col_{i}" for i in range(len(num_bands))]

        for i, b in enumerate(num_bands):
            name = cnames[i] if i < len(cnames) else f"col_{i}"
            bands.append((name, b[0], b[1]))

        return bands

    def words_to_rows(self, words: list[Word], page_width: float, report_type: str = "BS", expected_num_cols: Optional[int] = None, 
                      cached_bands: Optional[list[tuple[str, float, float]]] = None) -> tuple[list[Row], list[tuple[str, float, float]]]:
        """Dựng các Row từ Word của một trang: gom dòng -> tìm dòng bắt đầu vùng dữ liệu ->
        suy band -> gán mỗi word vào band (band items không nhận số nằm xa lề trái) ->
        nối các dòng tiêu chí bị xuống dòng (pending_items) và bỏ dòng header/footer;
        trả về (rows, bands).
        """
        lines = self.group_into_lines(words)
        start_idx = 0  # bắt đầu từ dòng đầu nếu không dò được dòng header
        for idx, line in enumerate(lines):
            line_text = " ".join(w.text for w in line).lower()
            if any(k in line_text for k in ["code", "mã số", "mã"]) and any(k in line_text for k in ["indicator", "chi tiêu", "items"]):
                start_idx = idx + 1
        for idx, line in enumerate(lines):
            has_fin = any(self.is_financial_number(w.text) and w.x0 > 150 for w in line)
            has_code = any(bool(RE_CODE.match(w.text.strip())) and w.x0 > 50 for w in line)
            if has_fin and has_code:
                start_idx = max(0, idx - 1)
                break  # dòng dữ liệu ĐẦU TIÊN; không ghi đè bằng các dòng sau
        data_lines = lines[start_idx:]

        bands = cached_bands
        if not bands:
            bands = self.infer_bands_from_data(data_lines, page_width, report_type, expected_num_cols)
        if not bands:
            return [], []

        abs_bands = [(n, s * page_width, e * page_width) for n, s, e in bands]
        raw_rows: list[Row] = []
        for line in data_lines:
            if not line:
                continue
            row = Row(sum(w.top + w.bottom for w in line) / (2 * len(line)))
            buckets = {n: [] for n, _, _ in abs_bands}
            for w in line:
                assigned = None
                cx = (w.x0 + w.x1) / 2
                is_fin = self.is_financial_number(w.text)
                for name, start, end in abs_bands:
                    if name == "items" and is_fin and w.x0 > 0.25 * page_width:
                        continue
                    a = w.x0 if name == "items" else w.x1
                    if start <= a <= end:
                        assigned = name
                        break
                if assigned is None:
                    valid_bands = [b for b in abs_bands if not (b[0] == "items" and is_fin and w.x0 > 0.25 * page_width)]
                    if not valid_bands:
                        valid_bands = abs_bands
                    assigned = min(valid_bands, key=lambda b: abs(cx - (b[1] + b[2]) / 2))[0]
                buckets[assigned].append(w)
            for name, ws in buckets.items():
                row.cells[name] = " ".join(x.text for x in sorted(ws, key=lambda x: x.x0)).strip()
            raw_rows.append(row)

        num_col_names = {b[0] for b in bands if b[0] not in ("items", "code", "notes")}
        merged: list[Row] = []
        pending_items = ""
        for row in raw_rows:
            full_text = " ".join(row.cells.values()).lower()
            if any(kw in full_text for kw in self.FOOTER_KW):
                break
            if any(kw in full_text for kw in ["indicator", "mã số", "thuyết minh", "closing balance", "opening balance", "số cuối kỳ", "số đầu năm", "số cuối năm", "this quarter", "accumulated balance", "chỉ tiêu", "đơn vị tính"]):
                continue

            items_text = row.cells.get("items", "").strip()
            code_text = row.cells.get("code", "").strip()
            has_code = bool(re.search(r"\d", code_text))
            has_numbers = any(bool(row.cells.get(c, "").strip().replace("-", "")) for c in num_col_names)
            is_section_header = bool(re.match(r'^\s*([A-E]|[IVXLCDM]+)[\.\-\–\—\s]', items_text)) or any(
                sec_kw in items_text.lower() for sec_kw in [
                    "tài sản ngắn hạn", "tài sản dài hạn", "nợ phải trả", "vốn chủ sở hữu",
                    "current assets", "non-current assets", "liabilities", "owner's equity", "equity",
                    "lưu chuyển tiền từ hoạt động", "cash flows from operating", "cash flows from investing", "cash flows from financing"
                ]
            )

            is_continuation = not has_code and not has_numbers and not is_section_header and bool(items_text)
            if is_continuation:
                if re.match(r'^\s*(?:\d+\s+)?(?:\d+|[a-z])[\.\)]', items_text):
                    pending_items = (pending_items + " " + items_text).strip()
                elif merged:
                    merged[-1].cells["items"] = (merged[-1].cells.get("items", "") + " " + items_text).strip()
                else:
                    pending_items = (pending_items + " " + items_text).strip()
            else:
                if pending_items:
                    row.cells["items"] = (pending_items + " " + items_text).strip()
                    pending_items = ""
                if row.cells.get("items", "").strip() or has_code or has_numbers:
                    merged.append(row)
        return merged, bands

    def clean_row(self, row: Row) -> dict:
        """Split cells that swallowed several numbers back across the columns.
        Làm sạch một Row thành dict chuẩn: tái phân bổ các ô số bị gộp trước, sau đó tách mã số
        (2-3 chữ số) khỏi cột code (phần còn lại là thuyết minh) và tách prefix (A-E/La Mã/số)
        khỏi tên chỉ tiêu.
        """
        num_names = [k for k in row.cells if k not in ("items", "code", "notes")]
        if not num_names:
            return None
        per_cell = {k: FIN_NUM_RE.findall(row.cells.get(k, "") or "") for k in num_names}
        flat = [t for k in num_names for t in per_cell[k]]
        # Chỉ tái phân bổ khi thực sự có ô bị gộp nhiều số. Trước đây hàm `return`
        # trần ở đây nên mọi dòng bình thường đều thành None và gây AttributeError
        # ở extract_table.
        if any(len(v) >= 2 for v in per_cell.values()) and flat:
            if len(flat) > len(num_names):
                self.warnings.append(
                    f"row has {len(flat)} values for {len(num_names)} columns "
                    f"({(row.cells.get('items') or '')[:40]!r}); keeping first {len(num_names)}")
            for i, k in enumerate(num_names):
                row.cells[k] = flat[i] if i < len(flat) else ""

        code_raw = row.cells.get("code", "").strip()
        notes_raw = row.cells.get("notes", "").strip()

        m = re.search(r"\b(\d{2,3}[a-zA-Z]?)\b", code_raw)
        if m:
            ma_so = m.group(1)
            remaining = code_raw.replace(ma_so, "").strip()
            if remaining and not notes_raw:
                notes_raw = remaining
        else:
            ma_so = code_raw

        items_raw = row.cells.get("items", "").strip()
        prefix = None
        m_pref = PREFIX_PATTERN.match(items_raw)
        if m_pref:
            prefix = m_pref.group(1)
            items_raw = items_raw[m_pref.end():].strip()

        result = {
            "prefix": prefix,
            "chi_tieu": items_raw,
            "ma_so": ma_so if ma_so else None,
            "thuyet_minh": notes_raw if notes_raw else None,
        }
        for k, v in row.cells.items():
            if k not in ("items", "code", "notes"):
                val_str = v.strip() if v else ""
                result[k] = None if val_str in ("", "-") else val_str
        return result

    def standardize_row(self, row_dict: dict, report_type: str) -> dict:
        new_row = dict(row_dict)
        new_row["Prefix"] = row_dict.get("prefix")
        new_row["Items"] = row_dict.get("chi_tieu")
        new_row["Code"] = row_dict.get("ma_so")
        new_row["Notes"] = row_dict.get("thuyet_minh")
        if report_type == "BS":
            new_row["period_current"] = row_dict.get("so_cuoi_ky")
            new_row["period_prior"] = row_dict.get("so_dau_nam")
        elif report_type == "CF":
            new_row["accum_current"] = row_dict.get("luy_ke_ky_nay")
            new_row["accum_prior"] = row_dict.get("luy_ke_ky_truoc")
        elif report_type == "PL":
            new_row["period_current"] = row_dict.get("ky_nay")
            new_row["period_prior"] = row_dict.get("ky_truoc")
            new_row["accum_current"] = row_dict.get("luy_ke_ky_nay")
            new_row["accum_prior"] = row_dict.get("luy_ke_ky_truoc")
        return new_row

    def sanitize_numbers(self, payload: dict, fields) -> dict:
        """Coerce OCR-noisy numeric cells so model construction cannot fail."""
        out = dict(payload)
        for f in fields:
            if f in out:
                num, warn = coerce_financial(out[f])
                if warn:
                    self.warnings.append(f"{f}: {warn}")
                out[f] = num
        return out

    def extract_table(self, file_path: str, page_start: int, page_end: int, report_type: str,
                      scope: Optional[str] = None, period_key: Optional[str] = None) -> list[dict]:
        """Trích toàn bộ bảng của một khoảng trang: đọc word từ PDF; trang không có số tài chính thì
        OCR (image_to_data + scale toạ độ về point); gom dòng rồi chuyển Row -> dict chuẩn hoá,
        ghép kết quả nhiều trang; trả list dict.
        """
        all_rows = []
        cached_bands = None
        with pdfplumber.open(file_path) as pdf:
            for page_num in range(page_start, page_end + 1):
                page = pdf.pages[page_num]
                p_dedup = page.dedupe_chars()
                w_pt = float(page.width)

                words_raw = p_dedup.extract_words()
                words = [Word(w["text"], w["x0"], w["x1"], w["top"], w["bottom"]) for w in words_raw]
                rows, bands = self.words_to_rows(words, w_pt, report_type, cached_bands=cached_bands)
                if bands and not cached_bands:
                    cached_bands = bands

                for r in rows:
                    # Gộp dấu câu bị nhân đôi (dòng fake-bold) trước khi tách ô.
                    for name in list(r.cells):
                        r.cells[name] = DOUBLED_PUNCT_RE.sub(r"\1", r.cells[name])
                    c = self.clean_row(r)
                    if not c:
                        continue
                    if not c.get("chi_tieu") and not c.get("ma_so"):
                        continue
                    row_out = self.standardize_row(c, report_type)
                    row_out["scope"] = scope
                    row_out["period_key"] = period_key
                    all_rows.append(row_out)
        return all_rows

    def extract_balance_sheet(self, file_path: str, page_start: int, page_end: int, year: Optional[int] = None,
                              scope: Optional[str] = None, period_key: Optional[str] = None) -> BalanceSheet:
        """Dựng model BalanceSheet từ raw rows: xếp từng dòng vào section A/B/C/D theo prefix/tên mục,
        gán các chỉ tiêu tổng theo mã số (100/200/270/300/400/440); số liệu được làm sạch OCR
        trước khi khởi tạo BalanceSheetLine.
        """
        raw_rows = self.extract_table(file_path, page_start, page_end, "BS", scope=scope, period_key=period_key)
        bs = BalanceSheet(page_start=page_start, page_end=page_end, year=year, scope=scope, period_key=period_key)
        bs.raw_data = raw_rows

        sections: Dict[str, List[BalanceSheetLine]] = {
            "A. TÀI SẢN NGẮN HẠN": [],
            "B. TÀI SẢN DÀI HẠN": [],
            "C. NỢ PHẢI TRẢ": [],
            "D. VỐN CHỦ SỞ HỮU": [],
        }
        current_section = "A. TÀI SẢN NGẮN HẠN"

        for row in raw_rows:
            prefix = row.get("prefix")
            items = (row.get("chi_tieu") or "").lower()

            if prefix == "A" or ("tài sản ngắn hạn" in items) or ("current assets" in items and "non-current" not in items):
                current_section = "A. TÀI SẢN NGẮN HẠN"
            elif prefix == "B" or ("tài sản dài hạn" in items) or ("non-current assets" in items):
                current_section = "B. TÀI SẢN DÀI HẠN"
            elif prefix == "C" or ("nợ phải trả" in items) or ("liabilities" in items):
                current_section = "C. NỢ PHẢI TRẢ"
            elif prefix == "D" or ("vốn chủ sở hữu" in items) or ("owner's equity" in items) or ("equity" in items and "debt" not in items):
                current_section = "D. VỐN CHỦ SỞ HỮU"

            payload = self.sanitize_numbers({
                "prefix": row.get("prefix"),
                "chi_tieu": row.get("chi_tieu") or "",
                "ma_so": row.get("ma_so"),
                "thuyet_minh": row.get("thuyet_minh"),
                "so_cuoi_ky": row.get("so_cuoi_ky") or row.get("period_current"),
                "so_dau_nam": row.get("so_dau_nam") or row.get("period_prior"),
            }, BS_NUM_FIELDS)
            try:
                line = BalanceSheetLine(**payload)
            except Exception as exc:
                self.warnings.append(f"BS row skipped (ma_so={row.get('ma_so')}): {exc}")
                continue
            sections[current_section].append(line)

            code = row.get("ma_so")
            val = payload.get("so_cuoi_ky")
            if code == "100":
                bs.tai_san_ngan_han = val
            elif code == "200":
                bs.tai_san_dai_han = val
            elif code in ("270", "280"):
                # Tổng tài sản: 270 theo TT 200/2014, 280 theo TT 99/2025.
                # Ở TT 99/2025 mã 270 là "Other non-current assets" (chỉ tiêu con)
                # nên chỉ nhận 270 khi dòng đó thực sự là dòng TỔNG.
                label = (row.get("chi_tieu") or "").upper()
                if code == "280" or "TOTAL" in label or "TỔNG" in label:
                    bs.tong_tai_san = val
                elif bs.tong_tai_san is None:
                    bs.tong_tai_san = val
            elif code == "300":
                bs.no_phai_tra = val
            elif code == "400":
                bs.von_chu_so_huu = val
            elif code == "440":
                bs.tong_nguon_von = val

        bs.sections = sections
        return bs

    def extract_income_statement(self, file_path: str, page_start: int, page_end: int, year: Optional[int] = None,
                                 scope: Optional[str] = None, period_key: Optional[str] = None) -> IncomeStatement:
        """Dựng model IncomeStatement từ raw rows: mỗi dòng thành IncomeStatementLine và
        gán các chỉ tiêu tổng theo mã số (01/02-03/10/11/20/21/22/25/26/30/50/51-52/60).
        """
        raw_rows = self.extract_table(file_path, page_start, page_end, "PL", scope=scope, period_key=period_key)
        pl = IncomeStatement(page_start=page_start, page_end=page_end, year=year, scope=scope, period_key=period_key)
        pl.raw_data = raw_rows

        line_items = []
        for row in raw_rows:
            payload = self.sanitize_numbers({
                "stt": row.get("prefix"),
                "chi_tieu": row.get("chi_tieu") or "",
                "ma_so": row.get("ma_so"),
                "thuyet_minh": row.get("thuyet_minh"),
                "ky_nay": row.get("ky_nay") or row.get("period_current"),
                "ky_truoc": row.get("ky_truoc") or row.get("period_prior"),
                "luy_ke_ky_nay": row.get("luy_ke_ky_nay") or row.get("accum_current"),
                "luy_ke_ky_truoc": row.get("luy_ke_ky_truoc") or row.get("accum_prior"),
            }, PL_NUM_FIELDS)
            try:
                line = IncomeStatementLine(**payload)
            except Exception as exc:
                self.warnings.append(f"PL row skipped (ma_so={row.get('ma_so')}): {exc}")
                continue
            line_items.append(line)

            field = match_pl_field(row.get("chi_tieu") or "", row.get("ma_so"))
            val = payload.get("ky_nay")
            if field == "cac_khoan_giam_tru":
                if pl.cac_khoan_giam_tru is None:
                    pl.cac_khoan_giam_tru = val
            elif field == "chi_phi_thue_tndn":
                # 51 (thuế hiện hành) và 52 (thuế hoãn lại): giữ giá trị dòng đầu tiên.
                if pl.chi_phi_thue_tndn is None:
                    pl.chi_phi_thue_tndn = val
            elif field:
                setattr(pl, field, val)

        pl.line_items = line_items
        return pl

    def extract_cash_flow(self, file_path: str, page_start: int, page_end: int, year: Optional[int] = None,
                          scope: Optional[str] = None, period_key: Optional[str] = None) -> CashFlowStatement:
        """Dựng model CashFlowStatement từ raw rows: xếp dòng vào 3 section I/II/III theo prefix/tên mục,
        gán các chỉ tiêu tổng theo mã số (20/30/40/50/60/70).
        """
        raw_rows = self.extract_table(file_path, page_start, page_end, "CF", scope=scope, period_key=period_key)
        cf = CashFlowStatement(page_start=page_start, page_end=page_end, year=year, scope=scope, period_key=period_key)
        cf.raw_data = raw_rows

        sections: Dict[str, List[CashFlowLine]] = {
            "I. LƯU CHUYỂN TIỀN TỪ HOẠT ĐỘNG KINH DOANH": [],
            "II. LƯU CHUYỂN TIỀN TỪ HOẠT ĐỘNG ĐẦU TƯ": [],
            "III. LƯU CHUYỂN TIỀN TỪ HOẠT ĐỘNG TÀI CHÍNH": [],
        }
        current_section = "I. LƯU CHUYỂN TIỀN TỪ HOẠT ĐỘNG KINH DOANH"

        for row in raw_rows:
            prefix = row.get("prefix")
            items = (row.get("chi_tieu") or "").lower()

            if prefix == "I" or ("kinh doanh" in items) or ("operating activities" in items):
                current_section = "I. LƯU CHUYỂN TIỀN TỪ HOẠT ĐỘNG KINH DOANH"
            elif prefix == "II" or ("đầu tư" in items) or ("investing activities" in items):
                current_section = "II. LƯU CHUYỂN TIỀN TỪ HOẠT ĐỘNG ĐẦU TƯ"
            elif prefix == "III" or ("tài chính" in items) or ("financing activities" in items):
                current_section = "III. LƯU CHUYỂN TIỀN TỪ HOẠT ĐỘNG TÀI CHÍNH"

            payload = self.sanitize_numbers({
                "prefix": row.get("prefix"),
                "chi_tieu": row.get("chi_tieu") or "",
                "ma_so": row.get("ma_so"),
                "thuyet_minh": row.get("thuyet_minh"),
                "luy_ke_ky_nay": row.get("luy_ke_ky_nay") or row.get("accum_current"),
                "luy_ke_ky_truoc": row.get("luy_ke_ky_truoc") or row.get("accum_prior"),
            }, CF_NUM_FIELDS)
            try:
                line = CashFlowLine(**payload)
            except Exception as exc:
                self.warnings.append(f"CF row skipped (ma_so={row.get('ma_so')}): {exc}")
                continue
            sections[current_section].append(line)

            code = row.get("ma_so")
            val = payload.get("luy_ke_ky_nay")
            if code == "20":
                cf.luu_chuyen_kinh_doanh = val
            elif code == "30":
                cf.luu_chuyen_dau_tu = val
            elif code == "40":
                cf.luu_chuyen_tai_chinh = val
            elif code == "50":
                cf.luu_chuyen_trong_ky = val
            elif code == "60":
                cf.tien_dau_ky = val
            elif code == "70":
                cf.tien_cuoi_ky = val

        cf.sections = sections
        return cf