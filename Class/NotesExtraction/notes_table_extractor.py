import re
import cv2
import numpy as np
import pdfplumber
from pdf2image import convert_from_path

from Class.TableExtractor import Word
from Class.NotesExtraction.heading_mapper import HeadingMapper
from Class.NotesExtraction.vertical_schedule_handler import VerticalScheduleHandler
from Class.NotesExtraction.ocr_handler import OCRHandler

class NotesTableExtractor:
    DASH_LIKE = {"-", "–", "—", ":", ".", "=", "·"}
    
    _HEADER_CELL_RE = re.compile(
        r"(?i)\b(dec|oct|jan|feb|mar|apr|may|jun|jul|aug|sep|nov)\.?[\s,.]?\d{0,2}\b|"
        r"as at|current period|previous period|amount|be paid off|payable amounts|"
        r"book value|historical cost|net book value|allocated amount|accumulated "
        r"depreciation|gross carrying amount|opening balance|closing balance|"
        r"beginning balance|ending balance|the period|in the period|unit\s*:?\s*vnd"
    )

    NOTES_COL_MAPS: dict = {
        "movement": {
            "period_current": "beginning_balance",
            "period_prior": "increase",
            "accum_current": "decrease",
            "accum_prior": "ending_balance",
        },
        "comparison": {
            "period_current": "current_year",
            "period_prior": "prior_year",
        },
        "loan": {
            "period_current": "outstanding_balance",
            "period_prior": "interest_rate",
            "accum_current": "maturity",
            "accum_prior": "collateral",
        },
    }

    HEADING_TO_COL_MAP: list[tuple[list[str], str]] = [
        (["fixed asset", "tangible", "intangible", "depreciation", "provision", "movement", "roll"], "movement"),
        (["loan", "borrowing", "finance lease", "debt"], "loan"),
        ([], "comparison")
    ]

    @classmethod
    def is_amount_token(cls, text):
        t = text.strip()
        if not t:
            return False
        if re.fullmatch(r"\d{1,3}([.,]\d{1,3})?%", t):
            return True
        digits = re.sub(r"[%,.() -]", "", t)
        return digits.isdigit() and len(digits) >= 3

    @classmethod
    def words_to_visual_rows(cls, words, tol=None):
        if not words:
            return []
        heights = sorted(w.bottom - w.top for w in words)
        med_h = heights[len(heights) // 2] or 10.0
        tol = tol if tol is not None else max(4.0, med_h * 0.6)
        rows = []
        for w in sorted(words, key=lambda w: w.top):
            if rows and w.top - rows[-1][0].top <= tol:
                rows[-1].append(w)
            else:
                rows.append([w])
        for r in rows:
            r.sort(key=lambda w: w.x0)
        return rows

    @classmethod
    def cluster_values(cls, values, tol):
        clusters = []
        for v in sorted(values):
            if clusters and v - sum(clusters[-1]) / len(clusters[-1]) <= tol:
                clusters[-1].append(v)
            else:
                clusters.append([v])
        return [sum(c) / len(c) for c in clusters]

    @classmethod
    def row_gap_boundaries(cls, row, page_w, gap_min=None):
        if gap_min is None:
            gap_min = max(8.0, 0.015 * page_w)
        mids = []
        for a, b in zip(row, row[1:]):
            gap = b.x0 - a.x1
            if gap >= gap_min:
                mids.append((a.x1 + b.x0) / 2.0)
        return mids

    @classmethod
    def cells_from_rows(cls, rows, boundaries, page_w):
        edges = [0.0] + sorted(boundaries) + [page_w]
        cells = [""] * (len(edges) - 1)
        # Handle the fact that rows could be a single row or list of rows
        if isinstance(rows[0], Word):
            rows = [rows]
            
        # Get median height from all words
        all_words = [w for r in rows for w in r]
        heights = sorted(w.bottom - w.top for w in all_words) if all_words else []
        med_h = heights[len(heights) // 2] if heights else 8.0
        gap_tol = max(1.2, med_h * 0.18)
        
        for row in rows:
            out = []
            for w in row:
                if out:
                    prev = out[-1]
                    gap = w.x0 - prev.x1
                    merge = gap <= gap_tol or (prev.text.rstrip().endswith(",") and w.text.strip().isdigit())
                    if merge:
                        prev.text = (prev.text + " " + w.text).strip()
                        prev.x1 = max(prev.x1, w.x1)
                        prev.bottom = max(prev.bottom, w.bottom)
                        continue
                out.append(w)
            for w in out:
                cx = (w.x0 + w.x1) / 2.0
                for i in range(len(edges) - 1):
                    if edges[i] <= cx < edges[i + 1]:
                        cells[i] = (cells[i] + " " + w.text).strip()
                        break
        return cells

    @classmethod
    def merge_multiline_header(cls, cells_rows):
        if len(cells_rows) < 2:
            return cells_rows
        i = 0
        header_block = []
        while i < len(cells_rows) and not any(cls.is_amount_token(c) for c in cells_rows[i]):
            header_block.append(cells_rows[i])
            i += 1
            if len(header_block) >= 4:
                break
        if len(header_block) <= 1:
            return cells_rows
        ncols = max(len(r) for r in header_block)
        merged = []
        for c in range(ncols):
            parts = [r[c].strip() for r in header_block if c < len(r) and r[c].strip()]
            merged.append(" ".join(parts))
        return [merged] + cells_rows[i:]

    @classmethod
    def is_table_block(cls, rows_out, boundaries):
        if not rows_out or not boundaries:
            return False
        ncols = len(boundaries) + 1
        amount_rows = 0
        for cells in rows_out:
            if any(cls.is_amount_token(cells[i])
                   for i in range(1, min(ncols, len(cells)))):
                amount_rows += 1
        amount_ratio = amount_rows / len(rows_out)
        prose_like_rows = 0
        for cells in rows_out:
            filled = sum(1 for i in range(ncols)
                         if i < len(cells) and len(cells[i].strip()) > 3)
            if filled == ncols:
                prose_like_rows += 1
        prose_ratio = prose_like_rows / len(rows_out)
        if amount_ratio >= 0.15:
            return True
        if prose_ratio > 0.6 and amount_ratio < 0.1:
            return False
        return True

    @classmethod
    def scan_column_count(cls, rows_out, boundaries, page_w):
        ncols = len(boundaries) + 1
        if ncols <= 2:
            return boundaries
        col_fill = [0] * ncols
        for cells in rows_out:
            for i in range(ncols):
                if i < len(cells):
                    val = cells[i].strip()
                    if val and val != "0" and val not in cls.DASH_LIKE:
                        col_fill[i] += 1
        threshold = max(1, int(len(rows_out) * 0.10))
        sorted_boundaries = sorted(boundaries)
        keep = []
        for bi, bx in enumerate(sorted_boundaries):
            left_col = bi
            right_col = bi + 1
            if col_fill[left_col] >= threshold and col_fill[right_col] >= threshold:
                keep.append(bx)
        return keep if keep else boundaries

    @classmethod
    def infer_boundaries(cls, bands, page_w, max_cols=8):
        contributions = []
        for bi, band in enumerate(bands):
            for row in band["rows"]:
                for mid in cls.row_gap_boundaries(row, page_w):
                    contributions.append((bi, mid))
        if not contributions:
            return []
        contributions.sort(key=lambda t: t[1])
        clusters = []
        for bi, mid in contributions:
            if clusters and mid - clusters[-1][1] / clusters[-1][2] <= 14.0:
                clusters[-1][1] += mid
                clusters[-1][2] += 1
            else:
                clusters.append([bi, mid, 1])
        chosen = []
        for _, total, n in clusters:
            avg = total / n
            if n >= 2 and 30.0 < avg < page_w - 30.0:
                chosen.append(avg)
        chosen.sort()
        res = []
        for c in chosen:
            if not res or c - res[-1] >= 28.0:
                res.append(c)
        return res[:max_cols]

    @classmethod
    def fallback_blocks(cls, visual_rows, page_w):
        blocks = []
        i, n = 0, len(visual_rows)
        while i < n:
            row = visual_rows[i]
            gaps = cls.row_gap_boundaries(row, page_w)
            has_amount = any(cls.is_amount_token(w.text) for w in row)
            if len(gaps) >= 2 or has_amount:
                start = i
                i += 1
                while i < n and (i - start) < 80:
                    prev = visual_rows[i - 1]
                    cur = visual_rows[i]
                    g2 = cls.row_gap_boundaries(cur, page_w)
                    line_h = (prev[0].bottom - prev[0].top) or 10.0
                    if g2 or (cur[0].top - prev[0].top) <= 3.0 * line_h:
                        i += 1
                    else:
                        break
                group = visual_rows[start:i]
                boundaries = cls.infer_boundaries([{"rows": group}], page_w)
                if not boundaries:
                    i = start + 1
                    continue
                rows_out = []
                for r in group:
                    cells = cls.cells_from_rows([r], boundaries, page_w)
                    if len([c for c in cells if c.strip()]) >= 2:
                        rows_out.append(cells)
                if rows_out:
                    rows_out = cls.merge_multiline_header(rows_out)
                    if not cls.is_table_block(rows_out, boundaries):
                        i = start + 1
                        continue
                    boundaries = cls.scan_column_count(rows_out, boundaries, page_w)
                    rows_out = []
                    for r in group:
                        cells = cls.cells_from_rows([r], boundaries, page_w)
                        if len([c for c in cells if c.strip()]) >= 2:
                            rows_out.append(cells)
                    rows_out = cls.merge_multiline_header(rows_out)
                    if rows_out:
                        blocks.append({"top": group[0][0].top, "bottom": group[-1][-1].bottom,
                                       "boundaries": boundaries, "cells_rows": rows_out, "visual_rows": group, "vertical": VerticalScheduleHandler._looks_vertical_schedule(rows_out, cls.is_amount_token)})
            else:
                i += 1
        return blocks
    
    @classmethod
    def page_blocks(cls, words, visual_rows, v_lines, h_lines, page_w):
        merged = [h_lines[0]]
        for v in h_lines[1:]:
            if v - merged[-1] < 4.0:
                continue
            merged.append(v)
        h_lines = merged
        if len(h_lines) >= 2:
            bands = []
            for a, b in zip(h_lines, h_lines[1:]):
                if b - a < 2.0:
                    continue
                inside = [w for w in words if a + 1.5 <= w.top and w.bottom <= b - 1.5]
                if not inside:
                    continue
                bands.append({"top": a, "bottom": b,
                              "rows": cls.words_to_visual_rows(inside)})
            groups = []
            for band in bands:
                if groups and band["top"] - groups[-1][-1]["bottom"] > 40.0:
                    groups.append([band])
                elif groups:
                    groups[-1].append(band)
                else:
                    groups.append([band])
            blocks = []
            for group in groups:
                if len(group) < 2:
                    continue
                boundaries = cls.infer_boundaries(group, page_w)
                if not boundaries:
                    continue
                rows_out = []
                for band in group:
                    for r in band['rows']:
                        cells = cls.cells_from_rows([r], boundaries, page_w)
                        if len([c for c in cells if c.strip()]) >= 2:
                            rows_out.append(cells)
                if rows_out:
                    rows_out = cls.merge_multiline_header(rows_out)
                    if not cls.is_table_block(rows_out, boundaries):
                        continue
                    boundaries = cls.scan_column_count(rows_out, boundaries, page_w)
                    rows_out = []
                    for band in group:
                        for r in band['rows']:
                            cells = cls.cells_from_rows([r], boundaries, page_w)
                            if len([c for c in cells if c.strip()]) >= 2:
                                rows_out.append(cells)
                    rows_out = cls.merge_multiline_header(rows_out)
                    if rows_out:
                        blocks.append({"top": group[0]["top"], "bottom": group[-1]["bottom"],
                                       "boundaries": boundaries, "cells_rows": rows_out, "visual_rows": [r for b in group for r in b["rows"]], "vertical": VerticalScheduleHandler._looks_vertical_schedule(rows_out, cls.is_amount_token)})
            if blocks:
                return blocks
        return cls.fallback_blocks(visual_rows, page_w)

    @classmethod
    def _is_header_cells(cls, cells) -> bool:
        if not cells:
            return False
        text = " ".join(c for c in cells if c).strip()
        if not text:
            return False
        if cls._HEADER_CELL_RE.search(text):
            return True
        if re.fullmatch(r"(?i)(?:[A-Za-z]{3,9}\.?[ ,.]*\d{1,2},?\s*){2,}", text.strip()):
            return True
        return False

    @classmethod
    def _drop_leading_header_rows(cls, cells_rows):
        if not cells_rows:
            return cells_rows
        k = 0
        while k < len(cells_rows) and cls._is_header_cells(cells_rows[k]):
            k += 1
            if k > 6:
                break
        return cells_rows[k:]

    @classmethod
    def _strip_leading_heading_rows(cls, cells_rows):
        if not cells_rows:
            return cells_rows, ""
        first = cells_rows[0]
        if any(cls.is_amount_token(c) for c in first[1:]):
            return cells_rows, ""
        text = " ".join(c.strip() for c in first if c and c.strip() not in
                        cls.DASH_LIKE and c.strip() != "0")
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            return cells_rows, ""
        cleaned = HeadingMapper._clean_heading(text)
        if not cleaned:
            return cells_rows, ""
        words = cleaned.split()
        if not re.match(r"^\d", cleaned) and len(words) < 2:
            return cells_rows, ""
        
        idx = 1
        while idx < len(cells_rows) and idx < 4:
            if any(cls.is_amount_token(c) for c in cells_rows[idx][1:]):
                break
            nxt = " ".join(c.strip() for c in cells_rows[idx] if c and c.strip() not in
                           cls.DASH_LIKE and c.strip() != "0")
            nxt_clean = HeadingMapper._clean_heading(re.sub(r"\s+", " ", nxt).strip())
            if nxt_clean and (re.match(r"^\d", nxt_clean) or len(nxt_clean.split()) >= 2):
                idx += 1
            else:
                break
        return cells_rows[idx:], cleaned

    @classmethod
    def _make_rows(cls, cells_rows, ncols):
        rows = []
        for cells in cells_rows:
            if not any(c.strip() for c in cells):
                continue
            row = {}
            row["chi_tieu"] = cells[0].strip() if cells and cells[0].strip() else ""
            for i in range(1, ncols):
                val = cells[i].strip() if i < len(cells) else ""
                row[f"col_{i}"] = "0" if (not val or val in cls.DASH_LIKE) else val
            rows.append(row)
        return rows

    @classmethod
    def extract_tables_from_pages(cls, file_path: str, page_start: int, page_end: int, dpi: int = 400) -> tuple[dict[str, list[dict]], dict[int, str]]:
        result: dict[str, list[dict]] = {}
        page_headings: dict[int, str] = {}
        carry_heading = ""
        with pdfplumber.open(file_path) as pdf:
            first_page = page_start + 1
            last_page = min(page_end + 1, len(pdf.pages))
            imgs = convert_from_path(file_path, dpi=dpi,
                                     first_page=first_page, last_page=last_page)
            for idx, page_num in enumerate(range(page_start, page_end + 1)):
                if idx >= len(imgs):
                    break
                page = pdf.pages[page_num]
                w_pt, h_pt = float(page.width), float(page.height)
                img = imgs[idx]
                page_text = (page.extract_text() or "").strip()
                words = []
                if page_text:
                    words = [Word(w["text"], w["x0"], w["x1"], w["top"], w["bottom"])
                             for w in page.extract_words() if w["text"].strip()]
                if not words:
                    words = OCRHandler.ocr_tokens_to_words(img, w_pt, h_pt)
                if not words:
                    continue
                visual_rows = cls.words_to_visual_rows(words)
                v_lines, h_lines = [], []
                if not page_text:
                    gray = np.array(img.convert("L"))
                    _, binv = cv2.threshold(gray, 0, 255,
                                            cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
                    h_px, w_px = binv.shape
                    sx, sy = w_pt / float(w_px), h_pt / float(h_px)
                    k_h_w = max(3, int(w_px * 0.18))
                    k_v_h = max(3, int(h_px * 0.05))
                    horiz = cv2.morphologyEx(binv, cv2.MORPH_OPEN,
                                            cv2.getStructuringElement(cv2.MORPH_RECT, (k_h_w, 1)))
                    vert = cv2.morphologyEx(binv, cv2.MORPH_OPEN,
                                            cv2.getStructuringElement(cv2.MORPH_RECT, (1, k_v_h)))
                    col_counts = vert.sum(axis=0)
                    v_px = [c for c in range(w_px) if col_counts[c] > 0]
                    v_lines = cls.cluster_values(v_px, max(2.0, 0.01 * w_px))
                    v_lines = [v * sx for v in v_lines]
                    row_counts = horiz.sum(axis=1)
                    h_px_rows = [r for r in range(h_px) if row_counts[r] > 0]
                    h_lines = cls.cluster_values(h_px_rows, max(2.0, 0.01 * h_px))
                    h_lines = [y * sy for y in h_lines]

                first_h_line = h_lines[0] if h_lines else None
                if first_h_line is not None:
                    header_rows =  [r for r in visual_rows if r[-1].bottom <= first_h_line + 4.0]
                else:
                    header_rows = []
                page_heading = HeadingMapper._heading_from_rows(header_rows)
                page_heading = HeadingMapper._clean_heading(page_heading)
                if page_heading:
                    page_headings[page_num] = page_heading
                blocks = cls.page_blocks(words, visual_rows, v_lines, h_lines, w_pt)
                cur_heading = page_heading or carry_heading
                for block in blocks:
                    heading = HeadingMapper.heading_above(block, visual_rows)
                    heading = HeadingMapper._clean_heading(heading)
                    if not heading and page_heading:
                        heading = page_heading
                    cells_rows = block["cells_rows"]
                    cells_rows = cls._drop_leading_header_rows(cells_rows)
                    cells_rows, lead_heading = cls._strip_leading_heading_rows(cells_rows)
                    if not heading and lead_heading:
                        heading = lead_heading
                    if not heading:
                        title = HeadingMapper._title_above(block, visual_rows, cls.is_amount_token)
                        if title:
                            heading = title
                    if not heading:
                        heading = cur_heading
                    if heading and HeadingMapper.is_valid_section_key(heading):
                        cur_heading = heading
                        carry_heading = heading
                    table_rows = None
                    if block.get("vertical"):
                        table_rows = VerticalScheduleHandler._postprocess_vertical(block, heading, cls.is_amount_token, cls._make_rows)
                    
                    if table_rows is None:
                        ncols = len(block["boundaries"]) + 1
                        table_rows = cls._make_rows(cells_rows, ncols)
                    if not table_rows:
                        continue
                    key = heading if heading else f"Table_p{page_num}_r{len(result) + 1}"
                    if key in result:
                        result[key].extend(table_rows)
                    else:
                        result[key] = table_rows
        return result, page_headings

    @classmethod
    def rename_notes_columns(cls, rows: list[dict], heading: str) -> list[dict]:
        def detect_col_map_type(heading: str) -> str:
            h = heading.lower()
            for keywords, map_type in cls.HEADING_TO_COL_MAP:
                if not keywords:
                    return map_type
                if any(kw in h for kw in keywords):
                    return map_type
            return "comparison"

        map_type = detect_col_map_type(heading)
        col_map = cls.NOTES_COL_MAPS[map_type]
        renamed = []
        for row in rows:
            new_row = {}
            for k, v in row.items():
                if k in col_map:
                    new_name = col_map[k]
                    if new_name is None:
                        continue
                    new_row[new_name] = v
                else:
                    new_row[k] = v
            renamed.append(new_row)
        return renamed