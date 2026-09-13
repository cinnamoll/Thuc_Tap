import re
import copy

from parse_financial_number import parse_number

class VerticalScheduleHandler:
    # Các method bên dưới gọi ``cls.parse_number(...)`` nên phải expose hàm
    # parse của module thành class attribute (trước đây thiếu -> AttributeError).
    parse_number = staticmethod(parse_number)
    MATRIX_KEYWORDS = ("building", "machinery", "transportation", "office", "equipment", "tangible", "contributed capital", 
                        "share premium", "treasury", "undistributed", "development", "total")

    @classmethod
    def looks_vertical_schedule(cls, cells_rows, is_amount_token_func) -> bool:
        if not cells_rows:
            return False
        max_cols = max(len(r) for r in cells_rows)
        if max_cols > 3:
            return False
            
        for r in cells_rows[:4]:
            text_row = " ".join(c.lower() for c in r if c)
            matches = sum(1 for kw in cls.MATRIX_KEYWORDS if kw in text_row)
            if matches >= 2:
                return False

        single_amount_count = 0
        multi_amount_count = 0
        total_data_rows = 0
        for row in cells_rows:
            amounts = sum(1 for c in row if is_amount_token_func(c))
            if amounts > 0:
                total_data_rows += 1
                if amounts == 1:
                    single_amount_count += 1
                elif amounts >= 2:
                    multi_amount_count += 1
        if total_data_rows == 0 or multi_amount_count >= 2:
            return False
        return single_amount_count / total_data_rows >= 0.75

    @classmethod
    def postprocess_vertical(cls, block, heading: str, is_amount_token_func, make_rows_func):
        cells_rows = block.get("cells_rows", [])
        visual_rows = block.get("visual_rows", [])
        if not visual_rows and cells_rows:
            return make_rows_func(cells_rows, len(block.get("boundaries", [])) + 1)
        
        out = []
        current_groups = []
        current_periods = []
        h = heading.lower() if heading else ""
        is_measure_period = any(k in h for k in ["goodwill", "fixed asset", "tangible", "intangible", "construction in progress", "finance lease"])
        is_comparison = any(k in h for k in ["loan", "payable", "receivable", "unearned", "prepaid"])
        
        if not is_measure_period and not is_comparison:
            return make_rows_func(cells_rows, len(block.get("boundaries", [])) + 1)
        if len(block.get("boundaries", [])) > 2 or (cells_rows and max(len(r) for r in cells_rows) > 3):
            return make_rows_func(cells_rows, len(block.get("boundaries", [])) + 1)

        date_re = re.compile(r"(?:As at\s+)?((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4})", re.I)
        dates_found = []
        for r in visual_rows:
            r_txt = " ".join(w.text for w in r).strip()
            for m in date_re.finditer(r_txt):
                d_str = m.group(1).strip()
                if d_str not in dates_found:
                    dates_found.append(d_str)

        date_keys = []
        for d in dates_found:
            s = d.lower()
            s = re.sub(r"[.,/]", " ", s)
            k = "_".join(s.split())
            if k not in date_keys:
                date_keys.append(k)

        for row in visual_rows:
            heights = [w.bottom - w.top for w in row]
            med_h = heights[len(heights)//2] if heights else 10.0
            tol = max(4.0, 0.5 * med_h)
            merged = []
            for w in row:
                if merged and w.x0 - merged[-1].x1 <= tol:
                    merged[-1].text = (merged[-1].text + " " + w.text).strip()
                    merged[-1].x1 = max(merged[-1].x1, w.x1)
                    merged[-1].bottom = max(merged[-1].bottom, w.bottom)
                else:
                    merged.append(copy.deepcopy(w))

            text = " ".join(w.text for w in merged).strip()
            if not text: 
                continue
            
            low = text.lower().strip()
            if re.match(r"^(historical cost|cost|allocated amount|accumulated depreciation|amortization|net book value|book value|amount|balance|opening|closing|movements?)$", low, re.I):
                row_cls = "group"
            if re.match(r"^(as at\s+)?(oct(ober)?|dec(ember)?|jan|feb|mar|apr|may|jun|jul|aug|sep|current|previous|beginning|ending)[\s.,0-9]+$", low, re.I):
                row_cls = "period"
            if re.match(r"^(amount|be paid off|[\w\s]+\d{4})$", low, re.I) and ("amount" in low or "paid" in low or re.search(r"(dec|oct|jan)\.?\s*\d{1,2},?\s*\d{4}", low, re.I)):
                row_cls = "col_pair"
            else:
                row_cls = "data"
                
            if row_cls == "group":
                current_groups = [text]
            elif row_cls == "period":
                current_periods = [text]
            elif row_cls == "col_pair":
                current_periods = [text]
            else:
                amounts = []
                label_parts = []
                for w in merged:
                    if is_amount_token_func(w.text):
                        amounts.append(w.text)
                    else:
                        label_parts.append(w.text)
                
                label = " ".join(label_parts).strip()
                if not label: 
                    continue
                
                row_dict = {"title": label}
                if is_measure_period:
                    if current_groups: row_dict["group"] = current_groups[-1]
                    if current_periods: row_dict["period"] = current_periods[-1]
                    if amounts:
                        amt_key = date_keys[0] if date_keys else ("current_period" if "current" in (current_periods[-1] if current_periods else "").lower() else "amount")
                        row_dict[amt_key] = cls.parse_number(amounts[-1])
                    out.append(row_dict)
                elif is_comparison:
                    if current_periods: row_dict["period"] = current_periods[-1]
                    if len(amounts) == 1:
                        col_key = date_keys[0] if date_keys else "current_period"
                        row_dict[col_key] = cls.parse_number(amounts[0])
                    elif len(amounts) >= 2:
                        col_key_1 = date_keys[0] if len(date_keys) >= 1 else "current_period"
                        col_key_2 = date_keys[1] if len(date_keys) >= 2 else "previous_period"
                        row_dict[col_key_1] = cls.parse_number(amounts[0])
                        row_dict[col_key_2] = cls.parse_number(amounts[1])
                        for i in range(2, len(amounts)):
                            sub_key = date_keys[i] if i < len(date_keys) else f"period_sub_{i+1}"
                            row_dict[sub_key] = cls.parse_number(amounts[i])
                    out.append(row_dict)

        return out if out else None

    # @classmethod
    # def _is_vertical_heading(cls, heading: str) -> bool:
    #     if not heading:
    #         return False
    #     h = heading.lower()
    #     hints = ("goodwill", "fixed asset", "tangible", "intangible", "finance lease",
    #              "construction in progress", "depreciation", "movement", "roll")
    #     return any(k in h for k in hints)