"""
temp3.py - Data-driven column detection (khong phu thuoc COLUMN_BANDS hay keyword header).

Core idea:
  Thay vi dua vao keyword matching tren dong header (dễ sai voi header nhieu dong
  hoac OCR kem), approach nay nhin vao chinh CAC DONG DATA de tim ra vi tri cot:

  1. Extract words (native / OCR).
  2. Gom words thanh dong vat ly.
  3. Tim "data start": dong dau tien co ma so 2-3 chu so -> cat bo header phia tren.
  4. Tu data rows, lay TAT CA SO TAI CHINH (>= 6 chu so, right-aligned):
       cluster x1 cua chung -> moi cluster = 1 cot so.
  5. Tim "items boundary": dua tren x0 min cua cac so tai chinh -> cot items la
     phan ben trai do.
  6. Tim cot code/notes dua tren cluster cua so 2-3 chu so nam giua items va so lon.
  7. Build bands tu cac cluster tim duoc, nhan ten theo vi tri (trai -> phai).
  8. Assign, merge, clean.

Uu diem so voi keyword-header approach:
  - Hoat dong bat ke header co bao nhieu dong hay OCR co sai.
  - Tu dong phat hien 2, 4, 6... cot so (Balance Sheet, Income Statement, ...).
  - So tai chinh luon nam chinh xac vi right-aligned trong PDF/scan.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

import pdfplumber
import pytesseract
from pdf2image import convert_from_path


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class Word:
    text: str
    x0: float
    x1: float
    top: float
    bottom: float


@dataclass
class Row:
    top: float
    cells: dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# 1. Native text check
# ---------------------------------------------------------------------------
def page_has_native_text(page: "pdfplumber.page.Page", min_chars: int = 30) -> bool:
    return len(page.chars) >= min_chars


# ---------------------------------------------------------------------------
# 2. Extract words
# ---------------------------------------------------------------------------
def extract_words_native(page: "pdfplumber.page.Page") -> list[Word]:
    raw = page.extract_words(
        x_tolerance=1.5, y_tolerance=3,
        keep_blank_chars=False, use_text_flow=False,
    )
    return [Word(w["text"], w["x0"], w["x1"], w["top"], w["bottom"]) for w in raw]


def extract_words_ocr(pil_image, page_width_pt, page_height_pt, ocr_dpi,
                      lang="vie+eng") -> list[Word]:
    data = pytesseract.image_to_data(
        pil_image, lang=lang,
        output_type=pytesseract.Output.DICT,
        config="--psm 6",
    )
    sx = page_width_pt / pil_image.width
    sy = page_height_pt / pil_image.height
    words = []
    for i in range(len(data["text"])):
        text = data["text"][i].strip()
        conf = int(data["conf"][i]) if data["conf"][i] not in ("-1", "") else -1
        # Ha nguong confidence xuong 10 thay vi 40 vi nhieu so bi OCR cho conf rat thap (VD: 0 hoac 37)
        if not text or conf < 10:
            continue
        x = data["left"][i] * sx
        y = data["top"][i] * sy
        w = data["width"][i] * sx
        h = data["height"][i] * sy
        words.append(Word(text, x, x + w, y, y + h))
    return words


# ---------------------------------------------------------------------------
# 3. Group words into physical lines
# ---------------------------------------------------------------------------
def group_into_lines(words: list[Word]) -> list[list[Word]]:
    if not words:
        return []
    ws = sorted(words, key=lambda w: (w.top, w.x0))
    heights = [w.bottom - w.top for w in ws if w.bottom > w.top]
    tol = (sum(heights) / len(heights) if heights else 10.0) * 0.5

    lines, cur, line_top = [], [ws[0]], ws[0].top
    for w in ws[1:]:
        if abs(w.top - line_top) <= tol:
            cur.append(w)
        else:
            lines.append(cur)
            cur, line_top = [w], w.top
    lines.append(cur)
    return lines


# ---------------------------------------------------------------------------
# 4. Helpers: classify words
# ---------------------------------------------------------------------------
_RE_FINANCIAL = re.compile(
    r"^\(?\d[\d,. ]{4,}\d\)?$"   # so tai chinh: >= 6 ky tu so+dinh dang
)
_RE_CODE = re.compile(r"^\d{2,3}$")        # ma so: 2-3 chu so
_RE_NOTES_NUM = re.compile(r"^\d{1,2}$")   # ghi chu: 1-2 chu so


def is_financial_number(text: str) -> bool:
    """So tai chinh lon: >= 6 chu so, co the chua ,./khoang trang/ngoac."""
    t = text.strip()
    digit_only = re.sub(r"[,.()\- ]", "", t)
    return bool(_RE_FINANCIAL.match(t)) and len(digit_only) >= 6


def is_code(text: str) -> bool:
    return bool(_RE_CODE.match(text.strip()))


def is_notes_num(text: str) -> bool:
    return bool(_RE_NOTES_NUM.match(text.strip()))


# ---------------------------------------------------------------------------
# 5. Cluster 1-D positions (gap-based)
# ---------------------------------------------------------------------------
def cluster_positions(
    positions: list[float],
    gap_pt: float,
) -> list[tuple[float, float]]:
    """
    Cluster 1-D float positions bang cach cat tai khoang cach > gap_pt.
    Tra ve list[(center_of_cluster, spread)] sap xep tang dan.
    Thuc ra tra ve (min, max) cua moi cluster.
    """
    if not positions:
        return []
    srt = sorted(positions)
    clusters: list[tuple[float, float]] = []
    lo = hi = srt[0]
    for p in srt[1:]:
        if p - hi > gap_pt:
            clusters.append((lo, hi))
            lo = hi = p
        else:
            hi = p
    clusters.append((lo, hi))
    return clusters


# ---------------------------------------------------------------------------
# 6. DATA-DRIVEN column band inference
# ---------------------------------------------------------------------------
def detect_data_start(lines: list[list[Word]]) -> int:
    """
    Tra ve index dong dau tien chua ma so (2-3 chu so) VA co it nhat 1 tu khac
    ben trai -> day la hang dau tien cua bang thuc su.
    Header / title nam phia tren.
    """
    for i, line in enumerate(lines):
        has_code = any(is_code(w.text) for w in line)
        has_text_left = any(w.x0 < min(w2.x0 for w2 in line if is_code(w2.text) or True) * 0.9
                            for w in line if not is_code(w.text))
        if has_code:
            return i
    return 0


def infer_bands_from_data(
    data_lines: list[list[Word]],
    page_width_pt: float,
) -> list[tuple[str, float, float]]:
    """
    Suy ra column bands tu cac dong data thuc su.
    """
    fin_words: list[Word] = []   # so tai chinh lon
    short_num_words: list[Word] = [] # ma so / notes (1-3 chu so)
    _RE_SHORT_NUM = re.compile(r"^[(]?\d{1,3}[a-zA-Z]?[)]?$")

    for line in data_lines:
        # phai co it nhat 1 so tai chinh tren dong nay moi xu ly
        fin_on_line = [w for w in line if is_financial_number(w.text)]
        if not fin_on_line:
            continue
        # x0 nho nhat cua so tai chinh tren dong nay
        min_fin_x0 = min(w.x0 for w in fin_on_line)
        fin_words.extend(fin_on_line)

        for w in line:
            if is_financial_number(w.text):
                continue
            # Nhat cac tu la so ngan nam TRUOC cot so tai chinh
            if _RE_SHORT_NUM.match(w.text.strip()) and w.x1 < min_fin_x0:
                short_num_words.append(w)

    if not fin_words:
        print("  [data-driven] Khong tim thay so tai chinh -> dung fallback bands")
        return _FALLBACK_BANDS

    # --- A. Cluster x1 cua so tai chinh -> cot so ---
    gap_pt = page_width_pt * 0.025   # khoang toi thieu giua 2 cot = 2.5% trang
    x1_clusters = cluster_positions([w.x1 for w in fin_words], gap_pt)

    # x0 min cua so tai chinh = diem bat dau vung so
    num_region_x0 = min(w.x0 for w in fin_words)

    print(f"  [data-driven] Tim thay {len(x1_clusters)} cot so, "
          f"vung so bat dau tai x0={num_region_x0:.1f}pt "
          f"({num_region_x0/page_width_pt*100:.1f}%)")

    # --- B. Boundary band cot so (lien tuc tu midpoint den midpoint) ---
    num_bands_raw = []
    for lo, hi in x1_clusters:
        cluster_words = [w for w in fin_words if lo - gap_pt <= w.x1 <= hi + gap_pt]
        col_x0 = min(w.x0 for w in cluster_words) if cluster_words else lo - gap_pt
        num_bands_raw.append((col_x0, hi))

    num_bands: list[tuple[float, float]] = []
    for idx, (x0, x1) in enumerate(num_bands_raw):
        if idx == 0:
            band_start = num_region_x0
        else:
            prev_x1 = num_bands_raw[idx - 1][1]
            band_start = (prev_x1 + x0) / 2
            
        if idx == len(num_bands_raw) - 1:
            band_end = page_width_pt
        else:
            next_x0 = num_bands_raw[idx + 1][0]
            band_end = (x1 + next_x0) / 2
            
        num_bands.append((band_start / page_width_pt, band_end / page_width_pt))

    # --- C. Phat hien code / notes tu cac so ngan (Code, Notes) ---
    code_band: Optional[tuple[float, float]] = None
    notes_band: Optional[tuple[float, float]] = None

    if short_num_words:
        # Cluster so ngan theo x1 (vi thuong can phai)
        short_clusters = cluster_positions([w.x1 for w in short_num_words], gap_pt)
        # Loai bo cac cluster nam tron trong vung so
        valid_short_clusters = [c for c in short_clusters if c[1] < num_region_x0]
        valid_short_clusters.sort(key=lambda c: c[0])
        
        # Lay toi da 2 cluster ngoai cung ben phai (sat voi vung so nhat)
        valid_short_clusters = valid_short_clusters[-2:]

        if len(valid_short_clusters) == 2:
            c0, c1 = valid_short_clusters
            # Trai la Code, Phai la Notes
            code_band = (c0[0] - gap_pt, c0[1] + gap_pt)
            notes_band = (c1[0] - gap_pt, c1[1] + gap_pt)
            
            # Chuan hoa ranh gioi de khong overlap
            code_band = (code_band[0]/page_width_pt, min(code_band[1], c1[0])/page_width_pt)
            notes_band = (min(code_band[1], notes_band[0]/page_width_pt), min(notes_band[1], num_region_x0)/page_width_pt)
            
        elif len(valid_short_clusters) == 1:
            c0 = valid_short_clusters[0]
            # Neu chi co 1 cot ngan, ta gan ten la code_band, ham clean_row_auto se tu phan tich ra code/notes
            code_band = ((c0[0] - gap_pt)/page_width_pt, min(c0[1] + gap_pt, num_region_x0)/page_width_pt)

    # --- D. Build final bands ---
    bands: list[tuple[str, float, float]] = []

    # items: tu 0 den start cua code (hoac start cua so neu khong co code)
    items_end = code_band[0] if code_band else (num_bands[0][0] if num_bands else 0.5)
    bands.append(("items", 0.0, items_end))

    if code_band:
        bands.append(("code", code_band[0],
                      notes_band[0] if notes_band else num_bands[0][0]))
    if notes_band:
        bands.append(("notes", notes_band[0],
                      num_bands[0][0] if num_bands else notes_band[1]))

    # Them cac cot so
    num_col_names = ["period_current", "period_prior",
                     "accum_current", "accum_prior",
                     "num_col_4", "num_col_5"]
    for i, (s, e) in enumerate(num_bands):
        col_name = num_col_names[i] if i < len(num_col_names) else f"num_col_{i}"
        bands.append((col_name, s, e))

    # Phu luc: dam bao khong co gap / overlap lon
    bands.sort(key=lambda b: b[1])

    print("  [data-driven] Bands suy ra:")
    for b in bands:
        print(f"    {b[0]:20s}: [{b[1]*100:5.1f}% - {b[2]*100:5.1f}%]")

    return bands


# Fallback bands (Balance Sheet layout)
_FALLBACK_BANDS: list[tuple[str, float, float]] = [
    ("items",          0.00, 0.50),
    ("code",           0.50, 0.58),
    ("notes",          0.58, 0.68),
    ("period_current", 0.68, 0.83),
    ("period_prior",   0.83, 1.00),
]

# Anchor mode cho tung kieu cot
_COL_ANCHOR: dict[str, str] = {}  # default = "center" cho tat ca


def _anchor(w: Word, mode: str) -> float:
    if mode == "x0":
        return w.x0
    if mode == "x1":
        return w.x1
    return (w.x0 + w.x1) / 2


def assign_band(w: Word, abs_bands: list[tuple[str, float, float]]) -> str:
    # Anchor: items dung x0, so tai chinh dung x1, con lai dung center
    for name, start, end in abs_bands:
        if name == "items":
            a = w.x0
        elif name in ("period_current", "period_prior", "accum_current", "accum_prior") \
                or name.startswith("num_col"):
            a = w.x1
        else:
            a = (w.x0 + w.x1) / 2
        if start <= a < end:
            return name
    # Fallback: gan vao band gan nhat theo center
    cx = (w.x0 + w.x1) / 2
    return min(abs_bands, key=lambda b: abs(cx - (b[1] + b[2]) / 2))[0]


# ---------------------------------------------------------------------------
# 7. Footer detection
# ---------------------------------------------------------------------------
_FOOTER_KW = ["prepared", "chief", "general", "director", "accountant",
               "nguoi lap", "ke toan truong", "giam doc"]


def _is_footer(line: list[Word]) -> bool:
    joined = " ".join(w.text.lower() for w in line)
    return any(kw in joined for kw in _FOOTER_KW)


# ---------------------------------------------------------------------------
# 8. Main: words -> rows (data-driven)
# ---------------------------------------------------------------------------
def words_to_rows_auto(
    words: list[Word],
    page_width_pt: float,
) -> tuple[list[Row], list[tuple[str, float, float]]]:
    if not words:
        return [], _FALLBACK_BANDS

    lines = group_into_lines(words)

    # Tim data start -> cat header
    data_start_idx = detect_data_start(lines)
    print(f"  [data-driven] Data bat dau tu line index {data_start_idx} "
          f"(cat bo {data_start_idx} dong header)")
    data_lines = lines[data_start_idx:]

    # Cat footer
    footer_cut = len(data_lines)
    for i in range(len(data_lines) - 1, -1, -1):
        if _is_footer(data_lines[i]):
            footer_cut = i
        else:
            break
    if footer_cut < len(data_lines):
        print(f"  [data-driven] Cat bo {len(data_lines) - footer_cut} dong footer")
        data_lines = data_lines[:footer_cut]

    # Infer bands
    bands = infer_bands_from_data(data_lines, page_width_pt)

    # Abs bands
    abs_bands = [(name, s * page_width_pt, e * page_width_pt) for name, s, e in bands]

    # Build raw rows
    raw_rows: list[Row] = []
    for group in data_lines:
        row_top = min(w.top for w in group)
        row = Row(top=row_top)
        buckets: dict[str, list[Word]] = {n: [] for n, _, _ in abs_bands}
        for w in group:
            buckets[assign_band(w, abs_bands)].append(w)
        for name, ws in buckets.items():
            row.cells[name] = " ".join(x.text for x in sorted(ws, key=lambda x: x.x0)).strip()
        raw_rows.append(row)

    # Merge continuation lines (item text tren nhieu dong)
    num_col_names = {b[0] for b in bands
                     if b[0] not in ("items", "code", "notes")}
    merged: list[Row] = []
    for row in raw_rows:
        has_code = bool(re.search(r"\d", row.cells.get("code", "")))
        has_numbers = any(row.cells.get(c, "").strip() for c in num_col_names)
        items_text = row.cells.get("items", "").strip()
        if not has_code and not has_numbers and items_text and merged:
            merged[-1].cells["items"] = (
                merged[-1].cells.get("items", "") + " " + items_text).strip()
        elif items_text or has_code or has_numbers:
            merged.append(row)

    return merged, bands


# ---------------------------------------------------------------------------
# 9. Parse number
# ---------------------------------------------------------------------------
def parse_number(val: Optional[str]) -> Optional[float]:
    if val is None:
        return None
    s = val.strip()
    if not s or s == "-":
        return None
    negative = s.startswith("(") and s.endswith(")")
    if negative:
        s = s[1:-1]
        
    # Xoa sach toan bo khoang trang, dau phay, dau cham
    # Vi tien VND la so nguyen. Neu ban can doc so thap phan, se can logic phuc tap hon.
    s = re.sub(r'[ ,.]', '', s)
    
    try:
        result = float(s)
        # Sanity check: so VND thuc te < 1e15 (1 nghin ty ty)
        if abs(result) > 1e15:
            return None
        return -result if negative else result
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# 10. Clean row
# ---------------------------------------------------------------------------
def clean_row_auto(row: Row, bands: list[tuple[str, float, float]]) -> dict:
    code_raw = row.cells.get("code", "").strip()
    notes_raw = row.cells.get("notes", "").strip()

    # Ma so: 3 chu so
    m = re.search(r"\b(\d{3})\b", code_raw)
    if m:
        code = m.group(1)
        leftover = code_raw.replace(m.group(0), "").strip()
        if leftover and not notes_raw:
            notes_raw = leftover
    else:
        m2 = re.search(r"\b(\d{3})\b", notes_raw)
        if m2:
            code = m2.group(1)
            notes_raw = notes_raw.replace(m2.group(0), "").strip()
        else:
            code = code_raw

    notes_clean = re.sub(r"\s+", " ", notes_raw).strip()

    result: dict = {
        "chi_tieu": re.sub(r"\s+", " ", row.cells.get("items", "")).strip(),
        "ma_so": code,
        "notes": notes_clean,
    }

    # Them cac cot so theo thu tu (period_current, period_prior, accum_current, ...)
    num_cols = [b[0] for b in bands
                if b[0] not in ("items", "code", "notes")]
    for col in num_cols:
        raw = row.cells.get(col, "").strip()
        result[col] = parse_number(raw) if raw else None

    return result


# ---------------------------------------------------------------------------
# 11. Orchestrator
# ---------------------------------------------------------------------------
def extract_table_auto(
    pdf_path: str,
    page_index: int,
    ocr_dpi: int = 400,
    force_ocr: bool = False,
) -> list[dict]:
    with pdfplumber.open(pdf_path) as pdf:
        if page_index >= len(pdf.pages):
            raise IndexError(f"page_index={page_index} vuot qua {len(pdf.pages)} trang")
        page = pdf.pages[page_index]
        page_width_pt = float(page.width)
        n_chars = len(page.chars)

        if page_has_native_text(page) and not force_ocr:
            words = extract_words_native(page)
            print(f"[page {page_index}] native (n_chars={n_chars}) -> {len(words)} words")
        else:
            print(f"[page {page_index}] OCR (n_chars={n_chars}, dpi={ocr_dpi})")
            images = convert_from_path(
                pdf_path, dpi=ocr_dpi,
                first_page=page_index + 1, last_page=page_index + 1,
            )
            if not images:
                raise RuntimeError("convert_from_path() khong tra ve anh nao.")
            words = extract_words_ocr(
                images[0], page_width_pt, float(page.height), ocr_dpi)
            print(f"  -> OCR: {len(words)} words")

    if not words:
        return []

    rows, bands = words_to_rows_auto(words, page_width_pt)
    print(f"  -> {len(rows)} rows")
    cleaned = [clean_row_auto(r, bands) for r in rows if any(r.cells.values())]
    print(f"  -> {len(cleaned)} rows sau khi loc rong")
    return cleaned


# ---------------------------------------------------------------------------
# 12. Debug helper
# ---------------------------------------------------------------------------
def debug_words(pdf_path: str, page_index: int, max_words: int = 100, ocr_dpi: int = 400):
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[page_index]
        pw = float(page.width)
        if page_has_native_text(page):
            words = extract_words_native(page)
        else:
            imgs = convert_from_path(pdf_path, dpi=ocr_dpi,
                                     first_page=page_index + 1, last_page=page_index + 1)
            words = extract_words_ocr(imgs[0], pw, float(page.height), ocr_dpi)
    print(f"page_width_pt={pw:.1f}")
    for w in sorted(words, key=lambda x: x.top)[:max_words]:
        fin = " [FIN]" if is_financial_number(w.text) else ""
        cod = " [CODE]" if is_code(w.text) else ""
        print(f"  top={w.top:6.1f}  x=[{w.x0/pw*100:5.1f}%-{w.x1/pw*100:5.1f}%]"
              f"  '{w.text}'{fin}{cod}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    pdf_path = (
        "/home/cinnamoll/Code/BT_Thuc_Tap/dataset/"
        "1_sj1_2026_2_4_33ee1c5_en_sj1_consolidatedfinacialstatements_q1_2026_signed.pdf"
    )

    print("\n" + "=" * 70)
    print(f"AUTO-DETECT: page {10}")
    print("=" * 70)
    rows = extract_table_auto(pdf_path, 6)
    print()
    for r in rows:
            print(r)
