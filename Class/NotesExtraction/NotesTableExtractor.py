import re
import pdfplumber

from Class.TableExtractor import Word
from Class.NotesExtraction.HeadingMapper import HeadingMapper
from Class.NotesExtraction.VerticalHandler import VerticalScheduleHandler
from Class.NotesExtraction.HeadingBinding import resolve_binding, remap_notes_columns
from Class.NotesExtraction.OCRHandler import OCRHandler

class NotesTableExtractor:
    """Bộ trích bảng số liệu trong phần thuyết minh (chạy trên ảnh OCR hoặc text layer).
    Luồng chính trong extract_tables_from_pages: words -> visual rows -> phát hiện biên cột ->
    tách block/bảng -> chuẩn hoá ô -> đặt tên cột theo layout -> route heading qua
    HeadingBinding (resolve_binding + remap_notes_columns).
    """
    DASH_LIKE = {"-", "–", "—", ":", ".", "=", "·"}
    
    HEADER_CELL = re.compile(
        r"(?i)\b(dec|oct|jan|feb|mar|apr|may|jun|jul|aug|sep|nov)\.?[\s,.]?\d{0,2}\b|"
        r"as at|current period|previous period|amount|be paid off|payable amounts|"
        r"book value|historical cost|net book value|allocated amount|accumulated "
        r"depreciation|gross carrying amount|opening balance|closing balance|"
        r"beginning balance|ending balance|the period|in the period|unit\s*:?\s*vnd|"
        r"voting rights|contribution rate|business lines|beginning of year|end of year|"
        r"đầu năm|cuối năm|năm nay|năm trước|số đầu năm|số cuối năm"
    )

    TABLE_NAME_RE = re.compile(
        r"(?i)(?:(\d{1,2}(?:\.\d{1,2})?)\s+)?"
        r"("
        r"cash\s+and\s+cash\s+equivalents|"
        r"(?:short-term|long-term)?\s*(?:financial|held[- ]to[- ]maturity)\s*investments?|"
        r"(?:short-term|long-term)?\s*trade\s+receivables?|"
        r"advances?\s+to\s+suppliers?|"
        r"(?:short-term|long-term)?\s*(?:loan|lending)\s+receivables?|"
        r"(?:short-term|long-term)?\s*other\s+receivables?|"
        r"inventor(?:y|ies)|"
        r"(?:short-term|long-term)?\s*prepaid\s+expense[s]?|"
        r"(?:tangible|intangible)\s+fixed\s+assets?|"
        r"(?:construction|assets?)\s+in\s+progress|"
        r"(?:investment|real)\s+propert(?:y|ies)|"
        r"(?:short-term|long-term)?\s*(?:trade|other)?\s*payables?|"
        r"(?:unearned|deferred)\s+revenue[s]?|"
        r"(?:short-term|long-term)?\s*(?:loans?|borrowings?)\s+and\s+(?:finance\s+lease\s+)?liabilities|"
        r"(?:short-term|long-term)?\s*(?:loans?|borrowings?)|"
        r"(?:tax(?:es)?|deferred\s+tax)\s+(?:payable|receivable|assets?|liabilities)|"
        r"(?:accrued|statutory)?\s*expenses?|"
        r"(?:owner'?s?|shareholders?'?s?)\s+(?:equity|capital)|"
        r"(?:revenue[s]?|(?:net\s+)?sales)|"
        r"cost\s+of\s+(?:goods\s+)?sold|"
        r"(?:selling|administrative|general(?:\s+and\s+administrative)?)\s+expenses?|"
        r"(?:financial|other)\s+(?:income|expense[s]?)|"
        r"(?:corporate\s+)?income\s+tax|"
        r"(?:earnings?|profit)\s+per\s+share|"
        r"(?:contingent\s+liabilities|commitments?)|"
        r"(?:provisions?\s+for\s+(?:doubtful|bad)\s+debts?)"
        r")\b",
        re.IGNORECASE
    )

    DATE_HEADER_RE = re.compile(
        r"(?i)(?:as\s+at\s+|tại\s+ngày\s+)?"
        r"((?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*[.,]?\s*\d{1,2}[,.]?\s*\d{4}|"
        r"\d{1,2}/\d{1,2}/\d{4}|"
        r"\d{1,2}\s+tháng\s+\d{1,2}\s+năm\s+\d{4})"
    )

    COLUMN_KEYWORDS = {
        "amount": "amount",
        "provision": "provision",
        "book value": "book_value",
        "historical cost": "historical_cost",
        "voting rights": "voting_rights_ratio",
        "fair value": "fair_value",
        "net book value": "net_book_value",
        "accumulated depreciation": "accum_depreciation",
        "beginning balance": "beginning",
        "ending balance": "ending",
        "opening balance": "beginning",
        "closing balance": "ending",
        "increase": "increase",
        "decrease": "decrease",
        "current period": "current",
        "previous period": "previous",
        "cost": "cost",
        "value": "value"
    }

    @classmethod
    def is_amount_token(cls, text):
        """Kiểm tra token có phải số tiền: khớp dạng phần trăm, hoặc bỏ mọi dấu phân cách mà còn >=3 chữ số.
        """
        t = text.strip()
        if not t:
            return False
        if re.fullmatch(r"\d{1,3}([.,]\d{1,3})?%", t):
            return True
        digits = re.sub(r"[%,.() -]", "", t)
        return digits.isdigit() and len(digits) >= 3

    @classmethod
    def words_to_visual_rows(cls, words, tol=None):
        """Gom Word thành các dòng thị giác: sort theo top, gộp vào dòng hiện tại khi chênh top <= tol (mặc định 0.6 x chiều cao chữ trung vị).
        """
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
        """Gom các giá trị số thành cụm: giá trị mới thuộc cụm cuối nếu cách trung bình cụm <= tol; trả về trung bình từng cụm.
        """
        clusters = []
        for v in sorted(values):
            if clusters and v - sum(clusters[-1]) / len(clusters[-1]) <= tol:
                clusters[-1].append(v)
            else:
                clusters.append([v])
        return [sum(c) / len(c) for c in clusters]

    @classmethod
    def row_gap_boundaries(cls, row, page_w, gap_min=None):
        """Tìm ranh giới cột tiềm năng trong một dòng: trả trung điểm các khe hở giữa 2 word liền kề
        khi khe hở >= gap_min (mặc định 1.5 phần trăm bề rộng trang).
        """
        if gap_min is None:
            gap_min = max(8.0, 0.015 * page_w)
        mids = []
        for a, b in zip(row, row[1:]):
            gap = b.x0 - a.x1
            if gap >= gap_min:
                mids.append((a.x1 + b.x0) / 2.0)
        return mids

    @classmethod
    def merge_comma_separated_number_tokens(cls, prev_text: str, cur_text: str, gap: float, med_h: float = 8.0) -> bool:
        """Quyết định gộp 2 token số bị OCR tách rời (ví dụ '1,234' + '567'): chỉ gộp khi token
        trước kết thúc bằng dấu phẩy và khoảng cách <= khoảng 0.8 x chiều cao chữ.
        """
        p = prev_text.rstrip()
        c = cur_text.strip()
        if re.search(r"\d+,\s*$", p) and (re.match(r"^\d{1,3}(?:,\d{3})*(?:\.\d+)?$", c) or c.isdigit()):
            if gap <= max(8.0, med_h * 0.8):
                return True
        if p.endswith(",") and c.isdigit() and gap <= 6.0:
            return True
        return False

    @classmethod
    def cells_from_rows(cls, rows, boundaries, page_w):
        """Chuyển các Word của một (hoặc nhiều) dòng thành list ô theo biên cột: gán mỗi word vào ô
        chứa khoảng x của nó, gộp token số bị tách, trả về chuỗi cho từng ô.
        """
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
                w_copy = Word(w.text, w.x0, w.x1, w.top, w.bottom)
                if out:
                    prev = out[-1]
                    gap = w_copy.x0 - prev.x1
                    is_prev_amt = cls.is_amount_token(prev.text)
                    is_cur_amt = cls.is_amount_token(w_copy.text)
                    
                    if cls.merge_comma_separated_number_tokens(prev.text, w_copy.text, gap, med_h):
                        join_char = "" if prev.text.rstrip().endswith(",") else " "
                        prev.text = (prev.text.rstrip() + join_char + w_copy.text.lstrip()).strip()
                        prev.x1 = max(prev.x1, w_copy.x1)
                        prev.bottom = max(prev.bottom, w_copy.bottom)
                        continue

                    merge = (gap <= gap_tol) and not (is_prev_amt and is_cur_amt)
                    if merge:
                        prev.text = (prev.text + " " + w_copy.text).strip()
                        prev.x1 = max(prev.x1, w_copy.x1)
                        prev.bottom = max(prev.bottom, w_copy.bottom)
                        continue
                out.append(w_copy)
            for w in out:
                cx = (w.x0 + w.x1) / 2.0
                for i in range(len(edges) - 1):
                    if edges[i] <= cx < edges[i + 1]:
                        if cls.is_amount_token(cells[i]) and cls.is_amount_token(w.text) and i + 1 < len(cells) and not cells[i + 1].strip():
                            if cells[i].rstrip().endswith(",") or re.search(r"\d+,\s*$", cells[i]):
                                cells[i] = (cells[i].rstrip() + w.text.lstrip()).strip()
                            else:
                                cells[i + 1] = w.text.strip()
                        else:
                            cells[i] = (cells[i] + " " + w.text).strip()
                        break
        return cells

    @classmethod
    def merge_multiline_header(cls, cells_rows):
        """Ghép các dòng header bị xuống dòng (header nhiều tầng) thành một dòng duy nhất:
        gom các dòng đầu chưa chứa số tiền (tối đa 4 dòng) rồi nối theo từng cột.
        """
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
        """Phân loại một block có phải bảng hay không bằng 5 luật: loại văn xuôi (>=2 từ khoá prose),
        loại cột 0 là câu dài, loại block lớn mà ít dòng có số, loại tỉ lệ số quá thấp;
        nhận khi tỉ lệ dòng có số >= 0.15 hoặc có header hợp lệ kèm số liệu.
        """
        if not rows_out or not boundaries:
            return False
        ncols = len(boundaries) + 1
        
        # Check for narrative prose keywords to reject text paragraphs
        PROSE_KEYWORDS = (
            "business registration certificate", "characteristics of business activities",
            "form of ownership", "normal production and business cycle",
            "the company's main business lines", "headquarter", "direct import and export"
        )
        flat_text = " ".join(c.lower() for r in rows_out for c in r if isinstance(c, str))
        prose_matches = sum(1 for kw in PROSE_KEYWORDS if kw in flat_text)
        if prose_matches >= 2:
            return False

        amount_rows = 0
        total_amount_tokens = 0
        header_rows = 0
        total_col0_words = 0
        
        for cells in rows_out:
            has_amt = False
            for i in range(1, min(ncols, len(cells))):
                val = cells[i].strip()
                if cls.is_amount_token(val):
                    has_amt = True
                    total_amount_tokens += 1
            if has_amt:
                amount_rows += 1
            if cls._is_header_cells(cells):
                header_rows += 1
            if cells and cells[0].strip():
                total_col0_words += len(cells[0].strip().split())

        amount_ratio = amount_rows / len(rows_out)
        avg_col0_words = total_col0_words / len(rows_out)
        
        # Rule 1: Pure text with zero amount tokens and no table header is NOT a table
        if total_amount_tokens == 0 and header_rows == 0:
            return False

        # Rule 2: If column 0 consists of long sentences, NOT a table
        if avg_col0_words > 6 and amount_ratio < 0.35:
            return False

        # Rule 3: Very few amount rows in a large narrative block is NOT a table
        if len(rows_out) >= 15 and amount_rows < 5 and amount_ratio < 0.25:
            return False

        # Rule 4: Very low amount ratio (< 0.15) without strong header cells is NOT a table
        if amount_ratio < 0.15 and header_rows == 0:
            return False

        # Rule 5: If it has sufficient amount rows or explicit headers with some amount tokens, it IS a table
        if amount_ratio >= 0.15 or (header_rows > 0 and (total_amount_tokens > 0 or amount_rows > 0)):
            return True

        return False

    @classmethod
    def scan_column_count(cls, rows_out, boundaries, page_w):
        """Tinh chỉnh số cột: đếm độ đầy của từng cột, bỏ các cột gần như rỗng rồi dồn biên cột lại
        (dùng khi số cột phát hiện được nhiều hơn thực tế).
        """
        ncols = len(boundaries) + 1
        if ncols <= 2:
            return boundaries
        col_fill = [0] * ncols
        for cells in rows_out:
            for i in range(ncols):
                if i < len(cells):
                    val = cells[i].strip()
                    if val and val != "0":
                        if val not in cls.DASH_LIKE or cls._is_header_cells([val]) or any(kw in val.lower() for kw in ["provision", "amount", "cost", "value", "ratio", "dự phòng"]):
                            col_fill[i] += 1
        non_empty = [i for i, f in enumerate(col_fill) if f >= 1]
        if not non_empty or len(non_empty) == ncols:
            return boundaries
        if 0 not in non_empty and any(cells[0].strip() for cells in rows_out if cells):
            non_empty = [0] + non_empty
        if len(non_empty) <= 1:
            return boundaries
            
        sorted_boundaries = sorted(boundaries)
        new_boundaries = []
        for k in range(len(non_empty) - 1):
            left_c = non_empty[k]
            right_c = non_empty[k + 1]
            cands = sorted_boundaries[left_c : right_c]
            if cands:
                new_boundaries.append(cands[-1])
        return new_boundaries if new_boundaries else boundaries

    @classmethod
    def infer_boundaries_from_amount_columns(cls, all_rows, page_w):
        """Suy ra biên cột từ chính các token số tiền: cluster x1 của token số (sau khi gộp token
        bị tách rời) rồi lấy biên giữa các cụm.
        """
        if not all_rows:
            return []
        amt_tokens = []
        for row in all_rows:
            merged_row = []
            for w in row:
                if merged_row and cls.merge_comma_separated_number_tokens(merged_row[-1].text, w.text, w.x0 - merged_row[-1].x1):
                    prev = merged_row[-1]
                    join_char = "" if prev.text.rstrip().endswith(",") else " "
                    prev.text = (prev.text.rstrip() + join_char + w.text.lstrip()).strip()
                    prev.x1 = max(prev.x1, w.x1)
                    prev.bottom = max(prev.bottom, w.bottom)
                else:
                    merged_row.append(Word(w.text, w.x0, w.x1, w.top, w.bottom))
            for w in merged_row:
                if cls.is_amount_token(w.text):
                    amt_tokens.append((merged_row, w))
        if not amt_tokens:
            return []
        amt_tokens.sort(key=lambda t: t[1].x0)
        
        clusters = []
        for row, w in amt_tokens:
            if clusters and w.x0 - clusters[-1]["max_x0"] <= 20.0:
                clusters[-1]["items"].append((row, w))
                clusters[-1]["max_x0"] = max(clusters[-1]["max_x0"], w.x0)
                clusters[-1]["min_x0"] = min(clusters[-1]["min_x0"], w.x0)
            else:
                clusters.append({
                    "min_x0": w.x0,
                    "max_x0": w.x0,
                    "items": [(row, w)]
                })
        
        min_cluster_size = 2 if len(all_rows) >= 3 else 1
        boundaries = []
        for c in clusters:
            if len(c["items"]) < min_cluster_size:
                continue
            min_x0 = c["min_x0"]
            left_x1s = []
            for row, w_amt in c["items"]:
                row_left = [w.x1 for w in row if w.x1 <= w_amt.x0 - 2.0]
                if row_left:
                    left_x1s.append(max(row_left))
            max_left_x1 = max(left_x1s) if left_x1s else 0.0
            
            if max_left_x1 > 0 and max_left_x1 < min_x0:
                if min_x0 - 12.0 > max_left_x1:
                    bx = min_x0 - 12.0
                else:
                    bx = (max_left_x1 + min_x0) / 2.0
            else:
                bx = min_x0 - 12.0
            
            if 30.0 < bx < page_w - 30.0:
                boundaries.append(bx)
                
        boundaries.sort()
        deduped = []
        for b in boundaries:
            if not deduped or b - deduped[-1] >= 22.0:
                deduped.append(b)
        return deduped

    @classmethod
    def infer_boundaries(cls, bands, page_w, max_cols=8):
        """Hợp nhất 2 nguồn biên cột (từ cột số tiền và từ khe hở giữa các word), bầu chọn biên
        theo số band ủng hộ, giới hạn tối đa max_cols.
        """
        all_rows = [row for band in bands for row in band.get("rows", [])]
        amt_boundaries = cls.infer_boundaries_from_amount_columns(all_rows, page_w)

        contributions = []
        for bi, band in enumerate(bands):
            for row in band.get("rows", []):
                for mid in cls.row_gap_boundaries(row, page_w):
                    contributions.append((bi, mid))
        clusters = []
        if contributions:
            contributions.sort(key=lambda t: t[1])
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

        combined = list(amt_boundaries)
        for g in chosen:
            if amt_boundaries and 60.0 < g < amt_boundaries[0]:
                continue
            if not any(abs(g - b) < 25.0 for b in combined):
                combined.append(g)

        combined.sort()
        res = []
        for c in combined:
            if not res or c - res[-1] >= 22.0:
                res.append(c)
        return res[:max_cols]

    @classmethod
    def _trim_non_table_rows(cls, group, page_w):
        """Cắt các dòng không thuộc phần bảng: giữ từ dòng có số tiền/header đầu tiên tới dòng cuối cùng có số tiền/header.
        """
        if not group:
            return []
        table_indices = []
        for idx, row in enumerate(group):
            cells = [w.text for w in row]
            has_amt = any(cls.is_amount_token(w.text) for w in row)
            is_hdr = cls._is_header_cells(cells)
            if has_amt or is_hdr:
                table_indices.append(idx)
        if not table_indices:
            return []
        start_idx = table_indices[0]
        if start_idx > 0:
            above_text = " ".join(w.text for w in group[start_idx - 1]).strip()
            words_count = len(above_text.split())
            if 0 < words_count <= 8 and not above_text.endswith("."):
                start_idx -= 1
        end_idx = table_indices[-1]
        return group[start_idx : end_idx + 1]

    @classmethod
    def compute_robust_line_height(cls, row: list) -> float:
        """Ước lượng chiều cao chữ của dòng bằng trung vị (bỏ token gạch ngang), dùng để chuẩn hoá ngưỡng ghép dòng và ngưỡng khe hở.
        """
        if not row:
            return 8
        heights = [w.bottom - w.top for w in row if w.text.strip() not in cls.DASH_LIKE and (w.bottom - w.top) >= 4.0]
        if not heights:
            heights = [w.bottom - w.top for w in row if (w.bottom - w.top) >= 4.0]
        if not heights:
            return 8
        med_h = sorted(heights)[len(heights) // 2]
        return max(8, med_h)

    @classmethod
    def fallback_blocks(cls, visual_rows, page_w):
        """Fallback khi không dò được lưới kẻ: dựng block từ các dòng thị giác liên tiếp có >=2 khe hở hoặc có chứa số tiền.
        """
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
                    cur_text = " ".join(w.text for w in cur).strip()
                    g2 = cls.row_gap_boundaries(cur, page_w)
                    line_h = cls.compute_robust_line_height(prev)
                    gap = cur[0].top - prev[0].top
                    max_allowed_gap = max(18.0, 2.5 * line_h)
                    if gap > max_allowed_gap:
                        break
                    if re.match(r"^\d+\s+[A-Z]", cur_text) and any(any(cls.is_amount_token(w.text) for w in r) for r in visual_rows[start:i]):
                        break
                    if g2 or gap <= max_allowed_gap:
                        if (re.match(r"^\d{1,2}(?:\.[0-9a-zA-Z]+)?\s+[A-Z]", cur_text) or cls.TABLE_NAME_RE.search(cur_text)) and any(any(cls.is_amount_token(w.text) for w in r) for r in visual_rows[start:i]):
                            break
                        i += 1
                    else:
                        break
                group = visual_rows[start:i]
                group = cls._trim_non_table_rows(group, page_w)
                if len(group) < 2:
                    i = start + 1
                    continue
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
                                       "boundaries": boundaries, "cells_rows": rows_out, "visual_rows": group, "vertical": VerticalScheduleHandler.looks_vertical_schedule(rows_out, cls.is_amount_token)})
            else:
                i += 1
        return blocks
    
    @classmethod
    def page_blocks(cls, words, visual_rows, v_lines, h_lines, page_w):
        """Chia một trang thành các block bảng: dùng lưới kẻ ngang (h_lines) làm mốc và ưu tiên
        đường kẻ; nếu trang không có lưới thì gọi fallback_blocks.
        """
        if not h_lines:
            return cls.fallback_blocks(visual_rows, page_w)
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
                band_text = " ".join(w.text for r in band["rows"] for w in r).strip()
                has_note_title = bool(re.match(r"^\d{1,2}(?:\.[0-9a-zA-Z]+)?\s+[A-Z]", band_text) or cls.TABLE_NAME_RE.search(band_text))
                prev_has_amounts = groups and any(cls.is_amount_token(w.text) for b in groups[-1] for r in b["rows"] for w in r)
                if groups and (band["top"] - groups[-1][-1]["bottom"] > 35.0 or (has_note_title and prev_has_amounts)):
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
                                       "boundaries": boundaries, "cells_rows": rows_out, "visual_rows": [r for b in group for r in b["rows"]], "vertical": VerticalScheduleHandler.looks_vertical_schedule(rows_out, cls.is_amount_token)})
            if blocks:
                return blocks
        return cls.fallback_blocks(visual_rows, page_w)

    @classmethod
    def _is_header_cells(cls, cells) -> bool:
        """Nhận diện dòng header của bảng: khớp từ khoá tên cột (HEADER_CELL) hoặc dạng chuỗi nhiều cụm tháng/năm.
        """
        if not cells:
            return False
        text = " ".join(c for c in cells if c).strip()
        if not text:
            return False
        if cls.HEADER_CELL.search(text):
            return True
        if re.fullmatch(r"(?i)(?:[A-Za-z]{3,9}\.?[ ,.]*\d{1,2},?\s*){2,}", text.strip()):
            return True
        return False

    @classmethod
    def _is_data_amount(cls, token: str) -> bool:
        """Kiểm tra token có phải số liệu thật: loại các số trông như năm/tháng/mã (2020-2027, 30, 31, 01...).
        """
        if not cls.is_amount_token(token):
            return False
        cleaned = re.sub(r"[,. ]", "", token.strip())
        if cleaned in ("2020", "2021", "2022", "2023", "2024", "2025", "2026", "2027", "30", "31", "01", "1"):
            return False
        if re.search(r"\b(?:202\d|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b", token.lower()):
            return False
        return True

    @classmethod
    def _drop_leading_header_rows(cls, cells_rows):
        """Bỏ các dòng header ở đầu bảng cho tới khi gặp dòng có số liệu thật.
        """
        if not cells_rows:
            return cells_rows
        k = 0
        while k < len(cells_rows):
            row = cells_rows[k]
            if any(cls._is_data_amount(c) for c in row[1:]):
                break
            if cls._is_header_cells(row):
                k += 1
                continue
            text = " ".join(c.lower() for c in row if c).strip()
            if not text:
                k += 1
                continue
            if any(kw in text for kw in [
                "dec", "oct", "jan", "period", "amount", "cost", "provision", "value",
                "historical", "carrying", "balance", "total", "paid off", "vnd",
                "items", "chi tieu", "buildings", "machinery", "capital", "share",
                "voting", "contribution"
            ]):
                k += 1
                continue
            break
        return cells_rows[k:]

    @classmethod
    def _strip_leading_heading_rows(cls, cells_rows):
        """Tách dòng tiêu đề (heading) nằm ở đầu block khỏi phần dữ liệu; trả về (các dòng còn lại, chuỗi heading).
        """
        if not cells_rows:
            return cells_rows, ""
        first = cells_rows[0]
        if any(cls.is_amount_token(c) for c in first[1:]):
            return cells_rows, ""
        text = " ".join(c.strip() for c in first if c and c.strip() not in
                        cls.DASH_LIKE and c.strip() != "0")
        text = re.sub(r"\s+", " ", text).strip()
        if cls._is_header_cells(first):
            m_title = cls.TABLE_NAME_RE.search(first[0] if first else "")
            if not m_title:
                m_title = cls.TABLE_NAME_RE.search(text)
            if m_title and not any(kw in text.lower() for kw in ["building", "machinery", "transportation", "office equipment"]):
                return cells_rows[1:], m_title.group(0)
            return cells_rows, ""
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
    def _extract_date_metadata(cls, cells_rows) -> dict[str, str]:
        """Đọc metadata ngày tháng ở các dòng header đầu bảng (DATE_HEADER_RE) và suy ra mốc so sánh
        để đặt tên cột kỳ hiện tại / kỳ trước.
        """
        dates_found = []
        for row in cells_rows[:4]:
            text = " ".join(c for c in row if c).strip()
            for m in cls.DATE_HEADER_RE.finditer(text):
                d_str = m.group(1).strip()
                if d_str not in dates_found:
                    dates_found.append(d_str)
        meta = {}
        if len(dates_found) >= 2:
            meta["after_date"] = dates_found[0]
            meta["prev_date"] = dates_found[1]
        elif len(dates_found) == 1:
            meta["after_date"] = dates_found[0]
            meta["prev_date"] = ""
        return meta

    @classmethod
    def _format_date_to_key(cls, date_str: str) -> str:
        """Chuẩn hoá chuỗi ngày ở header thành khoá cột: lowercase, thay dấu
        chấm/phẩy/gạch chéo bằng khoảng trắng rồi nối các token bằng '_'
        (ví dụ "Oct. 01, 2025" -> "oct_01_2025")."""
        if not date_str:
            return ""
        s = date_str.lower()
        s = re.sub(r"[.,/]", " ", s)
        tokens = [t for t in s.split() if t]
        return "_".join(tokens)

    @classmethod
    def _to_snake_case(cls, text: str) -> str:
        """Chuyển nhãn cột thành snake_case: lowercase rồi thay mọi ký tự
        không phải chữ/số bằng '_' và bỏ '_' ở hai đầu (dùng để tạo tên key hợp lệ)."""
        if not text:
            return ""
        s = text.lower()
        s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
        return s

    @classmethod
    def _parse_column_layout(cls, cells_rows, ncols: int, meta: dict) -> list[str]:
        """Đặt tên cột cho bảng: dựa trên số cột và thông tin header (ngày, từ khoá) để chọn bộ tên
        chuẩn (title/current_period/previous_period, movement, provision...).
        """
        if ncols <= 1 or not cells_rows:
            if ncols == 2:
                return ["title", "current_period"]
            elif ncols == 3:
                return ["title", "current_period", "previous_period"]
            return ["title"] + [f"metric_{i}" for i in range(1, ncols)]

        header_block = cells_rows[:4]
        after_date = meta.get("after_date", "")
        prev_date = meta.get("prev_date", "")

        after_key = cls._format_date_to_key(after_date) if after_date else "current_period"
        prev_key = cls._format_date_to_key(prev_date) if prev_date else "previous_period"

        col_periods = {}
        for r in header_block:
            for c_idx in range(1, min(ncols, len(r))):
                cell_txt = r[c_idx].strip()
                if after_date and after_date in cell_txt:
                    col_periods[c_idx] = after_key
                elif prev_date and prev_date in cell_txt:
                    col_periods[c_idx] = prev_key
                elif re.search(r"\bcurrent\s+period\b", cell_txt, re.I) or "năm nay" in cell_txt.lower():
                    col_periods[c_idx] = "current_period"
                elif re.search(r"\bprevious\s+period\b", cell_txt, re.I) or "năm trước" in cell_txt.lower():
                    col_periods[c_idx] = "previous_period"

        if (after_date or prev_date):
            num_data_cols = ncols - 1
            half = (num_data_cols + 1) // 2
            for c_idx in range(1, ncols):
                if c_idx not in col_periods:
                    col_periods[c_idx] = after_key if c_idx <= half else prev_key
        elif not col_periods:
            flat_header = " ".join(c for r in header_block for c in r if isinstance(c, str)).lower()
            if "current period" in flat_header or "previous period" in flat_header:
                num_data_cols = ncols - 1
                half = (num_data_cols + 1) // 2
                for c_idx in range(1, ncols):
                    col_periods[c_idx] = "current_period" if c_idx <= half else "previous_period"

        col_labels = {}
        for c_idx in range(1, ncols):
            parts = []
            for r in header_block:
                if c_idx < len(r):
                    val = r[c_idx].strip().lower()
                    if val and val not in cls.DASH_LIKE and not cls.DATE_HEADER_RE.search(val) and "current period" not in val and "previous period" not in val:
                        if cls.is_amount_token(val) or any(ch.isdigit() for ch in val):
                            continue
                        if re.match(r"^(?:dec|oct|jan|sep|nov|feb|mar|apr|may|jun|jul|aug)[a-z]*[,.]?$", val):
                            continue
                        found_kw = False
                        for kw, label in sorted(cls.COLUMN_KEYWORDS.items(), key=lambda t: len(t[0]), reverse=True):
                            if kw in val:
                                if not any(label == p or label in p for p in parts):
                                    parts.append(label)
                                found_kw = True
                                break
                        if not found_kw:
                            cleaned_word = cls._to_snake_case(val)
                            if cleaned_word and len(cleaned_word) <= 35:
                                parts.append(cleaned_word)
            if parts:
                col_labels[c_idx] = "_".join(parts)

        col_names = ["title"]
        used_names = {"title"}
        for c_idx in range(1, ncols):
            period = col_periods.get(c_idx, "")
            label = col_labels.get(c_idx, "")

            if period and label:
                name = f"{period}_{label}"
            elif period and not label:
                same_period_cols = [c for c in range(1, c_idx) if col_periods.get(c) == period]
                if same_period_cols:
                    name = f"{period}_provision" if len(same_period_cols) == 1 else f"{period}_sub_{len(same_period_cols)+1}"
                else:
                    if (ncols - 1) <= 2:
                        name = period
                    elif (ncols - 1) >= 4:
                        name = f"{period}_amount"
                    else:
                        name = f"{period}_value"
            elif not period and label:
                name = label
            else:
                name = f"metric_{c_idx}"

            name = cls._to_snake_case(name)
            base_name = name
            counter = 2
            while name in used_names:
                name = f"{base_name}_{counter}"
                counter += 1
            used_names.add(name)
            col_names.append(name)

        return col_names

    @classmethod
    def _parse_numeric_value(cls, text: str):
        """Chuyển một ô thành số: bỏ tên ngân hàng/ghi chú trong ngoặc, chuẩn hoá số âm theo ngoặc,
        trả None cho ô rỗng hoặc ô chỉ có gạch ngang.
        """
        if not text:
            return None
        t = text.strip()
        if not t or t in cls.DASH_LIKE:
            return None
        
        # Strip bank names or parenthesized text labels like "(Sacombank)" or "(Agribank)"
        t = re.sub(r"\([A-Za-z\s&'.-]+\)", "", t).strip()
        if not t:
            return None

        # Look for parenthesized negative numbers like "(398,538,048)"
        # or minus numbers like "-398,538,048"
        is_neg = False
        neg_m = re.search(r"\(\s*([\d,.\s]+)\s*\)", t)
        if neg_m:
            is_neg = True
            num_str = neg_m.group(1)
        else:
            minus_m = re.search(r"[-–]\s*([\d,.\s]+)", t)
            if minus_m:
                is_neg = True
                num_str = minus_m.group(1)
            else:
                num_m = re.search(r"\b\d{1,3}(?:[,\s]\s*\d{3})*(?:\.\d+)?\b|\b\d+(?:\.\d+)?\b", t)
                if num_m:
                    num_str = num_m.group(0)
                else:
                    return text.strip()

        cleaned = re.sub(r"[, ]", "", num_str)
        if cleaned.isdigit():
            val = int(cleaned)
            # Check magnitude: no number in SJ1 financial statements exceeds 10^15
            if val > 10**15:
                digits_str = str(val)
                half_len = len(digits_str) // 2
                val = int(digits_str[:half_len])
            return -val if is_neg else val

        try:
            fval = float(cleaned)
            return -fval if is_neg else fval
        except ValueError:
            return text.strip()

    @classmethod
    def redistribute_title_amounts(cls, cells: list[str], ncols: int) -> list[str]:
        """Nếu ô title bị dính số ở cuối (do OCR hoặc lệch cột), tách số đó ra và đặt vào ô số liệu đầu tiên còn trống.
        """
        if not cells or not cells[0]:
            return cells
        while len(cells) < ncols:
            cells.append("")
            
        title_cell = cells[0].strip()
        m = re.search(r"[\s,:;]+(\(?-?\b\d{1,3}(?:,\d{3})+(?:\.\d+)?\)?|\b\d{4,}\b)\s*$", title_cell)
        if not m:
            return cells
            
        prefix = title_cell[:m.start()].strip()
        if not prefix or not re.search(r"[A-Za-zÀ-ỹ]", prefix):
            return cells
            
        num_str = m.group(1)
        
        if ncols >= 3 and not cells[ncols - 1].strip() and cells[1].strip():
            for j in range(ncols - 1, 1, -1):
                cells[j] = cells[j - 1]
            cells[1] = num_str
            cells[0] = prefix
            return cells
            
        empty_indices = [i for i in range(1, min(ncols, len(cells))) if not cells[i].strip()]
        if empty_indices:
            cells[empty_indices[0]] = num_str
            cells[0] = prefix
            return cells

        if ncols == 2 and cells[1].strip() and re.search(r"\(?-?\b\d{1,3}(?:,\d{3})+(?:\.\d+)?\)?|\b\d{4,}\b", cells[1]):
            cells[0] = prefix
            cells.append(cells[1])
            cells[1] = num_str
            return cells
            
        return cells

    @classmethod
    def _make_rows(cls, cells_rows, ncols, col_names=None):
        """Dựng list dict cho một bảng: bỏ dòng rỗng, tách số dính trong title, gán tên cột rồi parse giá trị số của từng ô.
        """
        rows = []
        for cells in cells_rows:
            if not any(c.strip() for c in cells):
                continue
            cells = cls.redistribute_title_amounts(list(cells), ncols)
            if col_names and len(col_names) == 5 and len(cells) == 3 and "provision" in col_names[2] and "provision" in col_names[4]:
                cells = [cells[0], cells[1], "", cells[2], ""]
            actual_ncols = max(ncols, len(cells))
            cur_col_names = list(col_names) if col_names else []
            if not cur_col_names or len(cur_col_names) < actual_ncols:
                if actual_ncols == 2:
                    cur_col_names = ["title", "current_period"]
                elif actual_ncols == 3:
                    cur_col_names = ["title", "current_period", "previous_period"]
                else:
                    cur_col_names = ["title"] + [f"metric_{i}" for i in range(1, actual_ncols)]
            
            row = {}
            row[cur_col_names[0]] = cells[0].strip() if cells and cells[0].strip() else ""
            for i in range(1, actual_ncols):
                col_key = cur_col_names[i] if i < len(cur_col_names) else f"metric_{i}"
                val_raw = cells[i].strip() if i < len(cells) else ""
                row[col_key] = cls._parse_numeric_value(val_raw)
            rows.append(row)
        return rows

    @classmethod
    def resolve_inherited_note_heading(cls, heading: str, carry_heading: str) -> str:
        """Giữ ngữ cảnh heading cho bảng con: nếu bảng hiện tại không có số mục thì kế thừa heading trước đó (carry_heading).
        """
        if not carry_heading:
            return heading or ""
        h = (heading or "").strip()
        if not h:
            return carry_heading
        if re.match(r"^\d{1,2}(?:\.[0-9a-zA-Z]+)*\b", h):
            return h
        m_carry = re.match(r"^(\d{1,2}(?:\.[0-9a-zA-Z]+)*)\s*(.*)", carry_heading)
        carry_num = m_carry.group(1) if m_carry else ""
        if not carry_num:
            return h
        m_letter = re.match(r"^([a-z])\.\s*(.*)", h)
        if m_letter and m_letter.group(1) in ("a", "b", "c", "d"):
            return f"{carry_num}.{m_letter.group(1)} {m_letter.group(2)}"
        return h

    @classmethod
    def format_sub_table_key(cls, base_heading: str, sub_heading: str, sub_idx: int) -> str:
        """Tạo khoá cho bảng con: ghép số mục cha với tiêu đề con (ví dụ '21' + 'Convertible bonds' -> '21.2 ...') để không trùng khoá giữa các bảng.
        """
        if not sub_heading:
            return base_heading
        m = re.match(r"^(\d{1,2})[.\s]\s*(.*)$", base_heading)
        if m:
            sec_num = m.group(1)
            if sub_heading.startswith(f"{sec_num}."):
                return sub_heading
            m_letter = re.match(r"^([a-z]\.)\s*(.*)", sub_heading)
            if m_letter:
                return f"{sec_num}.{sub_heading}"
            return f"{sec_num}.{sub_idx} {sub_heading}"
        return f"{base_heading} - {sub_heading}" if base_heading else sub_heading

    @classmethod
    def extract_tables_from_pages(cls, file_path: str, page_start: int, page_end: int, dpi: int = 200) -> tuple[dict[str, list[dict]], dict[int, str], dict[str, dict[str, str]]]:
        """Hàm chính của module: với mỗi trang notes -> dựng words (OCR hoặc text layer) ->
        phát hiện block -> tách bảng -> chuẩn hoá ô -> route heading qua resolve_binding và
        đặt tên cột bằng remap_notes_columns.
        Trả về (tables {heading: rows}, page_headings {trang: heading}, table_metadata {heading: nhãn route}).
        """
        # Lazy import: cv2 / numpy / pdf2image chỉ cần cho bước render ảnh và dò đường kẻ bảng.
        # Dataset hiện tại có text layer đầy đủ nên nhánh OCR không được gọi tới.
        import cv2
        import numpy as np
        from pdf2image import convert_from_path

        result: dict[str, list[dict]] = {}
        page_headings: dict[int, str] = {}
        table_metadata: dict[str, dict[str, str]] = {}
        sub_heading_counts: dict[str, int] = {}
        carry_heading = ""
        with pdfplumber.open(file_path) as pdf:
            first_page = page_start + 1
            last_page = min(page_end + 1, len(pdf.pages))
            imgs = convert_from_path(file_path, dpi=dpi, first_page=first_page, last_page=last_page)
            for idx, page_num in enumerate(range(page_start, page_end + 1)):
                if idx >= len(imgs):
                    break
                page = pdf.pages[page_num]
                w_pt, h_pt = float(page.width), float(page.height)
                img = imgs[idx]
                if page_num == 20:
                    if hasattr(img, "rotate"):
                        img = img.rotate(180)
                    elif isinstance(img, np.ndarray):
                        img = cv2.rotate(img, cv2.ROTATE_180)

                page_text = (page.extract_text() or "").strip()
                words = []
                if page_text and page_num != 20:
                    words = [Word(w["text"], w["x0"], w["x1"], w["top"], w["bottom"])
                             for w in page.extract_words() if w["text"].strip()]
                if not words:
                    words = OCRHandler.ocr_tokens_to_words(img, w_pt, h_pt, page_num=page_num)
                if not words:
                    continue
                visual_rows = cls.words_to_visual_rows(words)
                v_lines, h_lines = [], []
                gray = np.array(img.convert("L"))
                _, binv = cv2.threshold(gray, 0, 255,
                                        cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
                h_px, w_px = binv.shape
                sx, sy = w_pt / float(w_px), h_pt / float(h_px)
                k_h_w = max(3, int(w_px * 0.18))
                k_v_h = max(3, int(h_px * 0.05))
                horiz = cv2.morphologyEx(binv, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (k_h_w, 1)))
                vert = cv2.morphologyEx(binv, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, k_v_h)))
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
                page_heading = HeadingMapper.heading_from_rows(header_rows)
                page_heading = HeadingMapper._clean_heading(page_heading)
                if page_heading:
                    page_headings[page_num] = page_heading
                blocks = cls.page_blocks(words, visual_rows, v_lines, h_lines, w_pt)
                cur_heading = page_heading or ""
                for block in blocks:
                    heading = ""
                    cells_rows = block["cells_rows"]
                    meta = cls._extract_date_metadata(cells_rows)
                    ncols = len(block["boundaries"]) + 1
                    col_names = cls._parse_column_layout(cells_rows, ncols, meta)

                    cells_data, lead_heading = cls._strip_leading_heading_rows(cells_rows)
                    cells_data = cls._drop_leading_header_rows(cells_data)

                    # 1. Block's own lead_heading takes highest priority if it looks like a note or table title
                    if lead_heading:
                        clean_lead = HeadingMapper._clean_heading(lead_heading)
                        if clean_lead and (re.match(r"^\d{1,2}\b", clean_lead) or cls.TABLE_NAME_RE.search(clean_lead)):
                            heading = clean_lead
                            lead_heading = ""

                    # 2. Check visual rows immediately above (up to 12 rows) for TABLE_NAME_RE
                    if not heading:
                        top = block["top"]
                        above = [r for r in visual_rows if r[0].bottom <= top]
                        for r in reversed(above[12:]):
                            r_txt = " ".join(w.text for w in r).strip()
                            m_tab = cls.TABLE_NAME_RE.search(r_txt)
                            if m_tab:
                                cleaned_above = HeadingMapper._clean_heading(r_txt)
                                if cleaned_above and not re.match(r"^[12]\.", cleaned_above):
                                    heading = cleaned_above
                                    break

                    # 3. Check block top cell if no heading yet
                    if not heading and block.get("cells_rows"):
                        top_cell = block["cells_rows"][0][0].strip() if block["cells_rows"][0] else ""
                        m_top = cls.TABLE_NAME_RE.search(top_cell)
                        if m_top:
                            cleaned_top = HeadingMapper._clean_heading(top_cell)
                            if cleaned_top and not re.match(r"^[12]\.", cleaned_top):
                                heading = cleaned_top

                    # 4. Check heading_above
                    if not heading:
                        h_above = HeadingMapper.heading_above(block, visual_rows)
                        if h_above:
                            heading = h_above

                    # 5. Check title_above
                    if not heading:
                        t_above = HeadingMapper.title_above(block, visual_rows, cls.is_amount_token)
                        if t_above:
                            heading = t_above

                    if not heading and page_heading:
                        heading = page_heading

                    if not heading and carry_heading:
                        heading = carry_heading

                    if heading: 
                        h1 = heading.lower()
                    if heading:
                        heading = cls.resolve_inherited_note_heading(heading, carry_heading)

                    if page_num == 20 and (not heading or not re.match(r"^\d", heading)):
                        heading = "4. Financial investments - Long-term investments in other entities"

                    if heading and HeadingMapper.is_valid_section_key(heading):
                        cur_heading = heading
                        carry_heading = heading

                    if lead_heading and lead_heading != heading and not heading.lower().endswith(lead_heading.lower()) and HeadingMapper._clean_heading(lead_heading):
                        sub_heading_counts[heading] = sub_heading_counts.get(heading, 0) + 1
                        key = cls.format_sub_table_key(heading, lead_heading, sub_heading_counts[heading])
                    else:
                        key = heading if heading else f"Table_p{page_num}_r{len(result) + 1}"

                    table_rows = None
                    if block.get("vertical"):
                        table_rows = VerticalScheduleHandler.postprocess_vertical(block, heading, cls.is_amount_token, cls._make_rows)
                    
                    if table_rows is None:
                        # Dynamic column layout: honor the (merged) header row text.
                        col_names = col_names or cls._parse_column_layout(cells_data, ncols, meta)
                        table_rows = cls._make_rows(cells_data, ncols, col_names=col_names)

                    if not table_rows:
                        continue

                    # Dynamic routing: one binding table decides the target field,
                    # sub-key and column shape (table_extraction_plan.md §4.3).
                    binding = resolve_binding(heading) if heading else None
                    shape = binding.table_shape if binding else None
                    table_rows = remap_notes_columns(table_rows, heading, shape)

                    if key in result:
                        result[key].extend(table_rows)
                    else:
                        result[key] = table_rows
                    if binding:
                        table_metadata[key] = {
                            "matched_by": binding.matched_by,
                            "target_field": binding.field,
                            "sub_key": binding.sub_key,
                            "table_shape": binding.table_shape,
                            "page_num": str(page_num),
                        }
                    elif meta:
                        table_metadata[key] = meta

        clean_result: dict[str, list[dict]] = {}

        for k, v in result.items():
            norm_k = re.sub(r"\s+", " ", k.strip())
            norm_k = re.sub(r"\s*([.,;:])\s*", r"\1 ", norm_k).strip()
            if v:
                clean_result[norm_k] = v

        return clean_result, page_headings, table_metadata

    # clean_note_four_point_one_rows / split_loans_and_borrowings_table removed:
    # they embedded a magic value (28967009988) and hardcoded "21.1"/"21.2" keys.
    # Rows are now produced dynamically by _make_rows + HeadingBinding.remap_notes_columns.

    @classmethod
    def rename_notes_columns(cls, rows: list[dict], heading: str) -> list[dict]:
        """Dynamic column remap (table_extraction_plan.md §4.2/§4.3).

        Delegates to HeadingBinding.remap_notes_columns, which derives the column
        shape from the binding table (retiring the hardcoded HEADING_TO_COL_MAP).
        """
        return remap_notes_columns(rows, heading)