import os
import re
from typing import Optional, Any
import pdfplumber
import pytesseract
from pdf2image import convert_from_path

class Word:
    def __init__(self, text: str, x0: float, x1: float, top: float, bottom: float):
        self.text = text
        self.x0 = x0
        self.x1 = x1
        self.top = top
        self.bottom = bottom
    def __repr__(self):
        return f"Word('{self.text}', x0={self.x0:.1f}, x1={self.x1:.1f}, y={self.top:.1f})"

class Row:
    def __init__(self, y_center: float):
        self.y_center = y_center
        self.words: list[Word] = []
        self.cells: dict[str, str] = {}
    def __repr__(self):
        return f"Row(y={self.y_center:.1f}, cells={self.cells})"

class DataDrivenTableExtractor:
    def __init__(self):
        self.dpi = 400
        self._RE_FINANCIAL = re.compile(r"^\(?\d[\d,. ]{4,}\d\)?$")
        self._RE_CODE = re.compile(r"^\d{2,3}$")
        self._RE_NOTES_NUM = re.compile(r"^\d{1,2}$")
        self._RE_SHORT_NUM = re.compile(r"^[(]?\d{1,3}[a-zA-Z]?[)]?$")
        self._FOOTER_KW = ["tổng giám đốc", "kế toán trưởng", "người lập biểu",
                           "chief accountant", "general director", "prepared by",
                           "ho chi minh", "hà nội", "ngày", "tháng", "năm", "director"]

    def _is_financial_number(self, text: str) -> bool:
        t = text.strip()
        digit_only = re.sub(r"[,.()\- ]", "", t)
        return bool(self._RE_FINANCIAL.match(t)) and len(digit_only) >= 6

    def _parse_number(self, val: Optional[str]) -> Optional[float]:
        if val is None: return None
        s = val.strip()
        if not s or s == "-": return None
        negative = s.startswith("(") and s.endswith(")")
        if negative:
            s = s[1:-1]
        s = re.sub(r'[ ,.]', '', s)
        try:
            result = float(s)
            if abs(result) > 1e15: return None
            return -result if negative else result
        except ValueError:
            return None

    def _cluster_positions(self, positions: list[float], gap: float) -> list[tuple[float, float]]:
        if not positions: return []
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

    def _extract_words_ocr(self, img, page_width: float, page_height: float) -> list[Word]:
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
        img_w, img_h = img.size
        sx, sy = page_width / img_w, page_height / img_h
        words = []
        for i in range(len(data["text"])):
            text = data["text"][i].strip()
            conf = int(data["conf"][i]) if data["conf"][i] not in ("-1", "") else -1
            if not text or conf < 10:
                continue
            x = data["left"][i] * sx
            y = data["top"][i] * sy
            w = data["width"][i] * sx
            h = data["height"][i] * sy
            words.append(Word(text, x, x + w, y, y + h))
        return words

    def _group_into_lines(self, words: list[Word]) -> list[list[Word]]:
        if not words: return []
        words_sorted = sorted(words, key=lambda w: w.top)
        lines = []
        current_line = [words_sorted[0]]
        for w in words_sorted[1:]:
            prev = current_line[-1]
            if w.top < prev.bottom:
                current_line.append(w)
            else:
                current_line.sort(key=lambda x: x.x0)
                lines.append(current_line)
                current_line = [w]
        if current_line:
            current_line.sort(key=lambda x: x.x0)
            lines.append(current_line)
        return lines

    def _detect_data_start(self, lines: list[list[Word]]) -> int:
        for idx, line in enumerate(lines):
            has_fin = any(self._is_financial_number(w.text) for w in line)
            has_code = any(self._RE_CODE.match(w.text) for w in line)
            if has_fin and has_code:
                return max(0, idx - 1)
        return 0

    def _is_header_row(self, row: Row) -> bool:
        t = row.cells.get("items", "").lower()
        if "chỉ tiêu" in t or "items" in t or "mã số" in t or "code" in t:
            return True
        return False

    def _is_footer_row(self, row: Row) -> bool:
        t = row.cells.get("items", "").lower()
        if not t: return False
        return any(kw in t for kw in self._FOOTER_KW)

    def _infer_bands_from_data(self, data_lines: list[list[Word]], page_width: float) -> list[tuple[str, float, float]]:
        fin_words = []
        short_num_words = []
        
        for line in data_lines:
            fin_on_line = [w for w in line if self._is_financial_number(w.text)]
            if not fin_on_line: continue
            min_fin_x0 = min(w.x0 for w in fin_on_line)
            fin_words.extend(fin_on_line)
            for w in line:
                if self._is_financial_number(w.text): continue
                if self._RE_SHORT_NUM.match(w.text.strip()) and w.x1 < min_fin_x0:
                    short_num_words.append(w)

        if not fin_words:
            return []

        gap_pt = page_width * 0.025
        x1_clusters = self._cluster_positions([w.x1 for w in fin_words], gap_pt)
        num_region_x0 = min(w.x0 for w in fin_words)

        num_bands_raw = []
        for lo, hi in x1_clusters:
            cluster_words = [w for w in fin_words if lo - gap_pt <= w.x1 <= hi + gap_pt]
            col_x0 = min(w.x0 for w in cluster_words) if cluster_words else lo - gap_pt
            num_bands_raw.append((col_x0, hi))

        num_bands = []
        for idx, (x0, x1) in enumerate(num_bands_raw):
            band_start = num_region_x0 if idx == 0 else (num_bands_raw[idx - 1][1] + x0) / 2
            band_end = page_width if idx == len(num_bands_raw) - 1 else (x1 + num_bands_raw[idx + 1][0]) / 2
            num_bands.append((band_start / page_width, band_end / page_width))

        code_band = None
        notes_band = None
        if short_num_words:
            short_clusters = self._cluster_positions([w.x1 for w in short_num_words], gap_pt)
            valid_short_clusters = [c for c in short_clusters if c[1] < num_region_x0]
            valid_short_clusters.sort(key=lambda c: c[0])
            valid_short_clusters = valid_short_clusters[-2:]

            if len(valid_short_clusters) == 2:
                c0, c1 = valid_short_clusters
                code_band = ((c0[0] - gap_pt) / page_width, min(c0[1] + gap_pt, c1[0]) / page_width)
                notes_band = (min(code_band[1], (c1[0] - gap_pt) / page_width), min(c1[1] + gap_pt, num_region_x0) / page_width)
            elif len(valid_short_clusters) == 1:
                c0 = valid_short_clusters[0]
                code_band = ((c0[0] - gap_pt) / page_width, min(c0[1] + gap_pt, num_region_x0) / page_width)

        bands = []
        items_end = code_band[0] if code_band else num_bands[0][0]
        bands.append(("items", 0.0, items_end))
        if code_band: bands.append(("code", code_band[0], code_band[1]))
        if notes_band: bands.append(("notes", notes_band[0], notes_band[1]))
        
        cnames = ["period_current", "period_prior", "accum_current", "accum_prior"]
        for i, b in enumerate(num_bands):
            n = cnames[i] if i < len(cnames) else f"num_col_{i}"
            bands.append((n, b[0], b[1]))
            
        return bands

    def _assign_band(self, w: Word, abs_bands: list[tuple[str, float, float]]) -> str:
        for name, start, end in abs_bands:
            a = w.x0 if name == "items" else w.x1
            if start <= a <= end: return name
        cx = (w.x0 + w.x1) / 2
        return min(abs_bands, key=lambda b: abs(cx - (b[1] + b[2]) / 2))[0]

    def _words_to_rows(self, words: list[Word], page_width: float) -> list[Row]:
        lines = self._group_into_lines(words)
        start_idx = self._detect_data_start(lines)
        data_lines = lines[start_idx:]
        
        bands = self._infer_bands_from_data(data_lines, page_width)
        if not bands:
            return []

        abs_bands = [(n, s * page_width, e * page_width) for n, s, e in bands]
        raw_rows = []
        for line in data_lines:
            if not line: continue
            row = Row(sum(w.top + w.bottom for w in line) / (2 * len(line)))
            buckets = {n: [] for n, _, _ in abs_bands}
            for w in line:
                buckets[self._assign_band(w, abs_bands)].append(w)
            for name, ws in buckets.items():
                row.cells[name] = " ".join(x.text for x in sorted(ws, key=lambda x: x.x0)).strip()
            raw_rows.append(row)

        num_col_names = {b[0] for b in bands if b[0] not in ("items", "code", "notes")}
        merged = []
        for row in raw_rows:
            if self._is_header_row(row): continue
            if self._is_footer_row(row): break

            has_code = bool(re.search(r"\d", row.cells.get("code", "")))
            has_numbers = any(row.cells.get(c, "").strip() for c in num_col_names)
            items_text = row.cells.get("items", "").strip()
            if not has_code and not has_numbers and items_text and merged:
                merged[-1].cells["items"] = (merged[-1].cells.get("items", "") + " " + items_text).strip()
            elif items_text or has_code or has_numbers:
                merged.append(row)
        return merged

    def _clean_row(self, row: Row) -> dict:
        code_raw = row.cells.get("code", "").strip()
        notes_raw = row.cells.get("notes", "").strip()

        m = re.search(r"\b(\d{3})\b", code_raw)
        if m and not notes_raw:
            ma_so = m.group(1)
            notes_raw = code_raw.replace(ma_so, "").strip()
        else:
            ma_so = m.group(1) if m else code_raw

        items_raw = row.cells.get("items", "").strip()
        prefix = None
        prefix_match = re.compile(r'^([A-E]|[IVX]+|\d+)\.\s+').match(items_raw)
        if prefix_match:
            prefix = prefix_match.group(1)
            items_raw = items_raw[prefix_match.end():].strip()
        
        result = {
            "prefix": prefix,
            "chi_tieu": items_raw,
            "ma_so": ma_so,
            "notes": notes_raw,
        }
        for k, v in row.cells.items():
            if k not in ("items", "code", "notes"):
                result[k] = self._parse_number(v)
        return result

    def _standardize_row(self, row_dict: dict, report_type: str) -> dict:
        new_row = {
            "Prefix": row_dict.get("prefix", ""),
            "Chỉ tiêu": row_dict.get("chi_tieu", ""),
            "Mã số": row_dict.get("ma_so", ""),
            "Thuyết minh": row_dict.get("notes", "")
        }
        if report_type == "BS":
            new_row["Số cuối kỳ"] = row_dict.get("period_current")
            new_row["Số đầu năm"] = row_dict.get("period_prior")
        elif report_type == "PL":
            new_row["Kỳ này"] = row_dict.get("period_current")
            new_row["Kỳ trước"] = row_dict.get("period_prior")
        elif report_type == "CF":
            new_row["Lũy kế kỳ này"] = row_dict.get("accum_current") if "accum_current" in row_dict else row_dict.get("period_current")
            new_row["Lũy kế kỳ trước"] = row_dict.get("accum_prior") if "accum_prior" in row_dict else row_dict.get("period_prior")
        return new_row

    def extract_table(self, file_path: str, page_start: int, page_end: int, report_type: str) -> list[dict]:
        all_rows = []
        with pdfplumber.open(file_path) as pdf:
            imgs = convert_from_path(file_path, dpi=self.dpi, first_page=page_start+1, last_page=page_end+1)
            for i, page_num in enumerate(range(page_start, page_end + 1)):
                if i >= len(imgs): break
                page = pdf.pages[page_num]
                w_pt, h_pt = float(page.width), float(page.height)
                
                # Try text extraction first
                words_raw = page.extract_words()
                words = [Word(w["text"], w["x0"], w["x1"], w["top"], w["bottom"]) for w in words_raw]
                lines = self._group_into_lines(words)
                
                # Check if we need OCR
                has_fin = False
                for line in lines:
                    if any(self._is_financial_number(w.text) for w in line):
                        has_fin = True
                        break
                        
                if not has_fin:
                    words = self._extract_words_ocr(imgs[i], w_pt, h_pt)

                rows = self._words_to_rows(words, w_pt)
                for r in rows:
                    c = self._clean_row(r)
                    if not c.get("chi_tieu"): continue
                    # check if row is empty of numbers
                    if not any(v is not None for k, v in c.items() if k not in ('prefix', 'chi_tieu', 'ma_so', 'notes')):
                        # It might be a section header
                        pass
                    all_rows.append(self._standardize_row(c, report_type))
        return all_rows
