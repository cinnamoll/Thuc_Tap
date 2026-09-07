import re
import copy

class VerticalScheduleHandler:
    @classmethod
    def _looks_vertical_schedule(cls, cells_rows, is_amount_token_func) -> bool:
        if not cells_rows: return False
        single_amount_count = 0
        total_data_rows = 0
        for row in cells_rows:
            amounts = sum(1 for c in row if is_amount_token_func(c))
            if amounts > 0:
                total_data_rows += 1
                if amounts == 1:
                    single_amount_count += 1
        if total_data_rows == 0: return False
        return single_amount_count / total_data_rows >= 0.6

    @classmethod
    def _classify_vertical_row(cls, text: str) -> str:
        low = text.lower().strip()
        if re.match(r"^(historical cost|cost|allocated amount|accumulated depreciation|amortization|net book value|book value|amount|balance|opening|closing|movements?)$", low, re.I):
            return "group"
        if re.match(r"^(as at\s+)?(oct(ober)?|dec(ember)?|jan|feb|mar|apr|may|jun|jul|aug|sep|current|previous|beginning|ending)[\s.,0-9]+$", low, re.I):
            return "period"
        if re.match(r"^(amount|be paid off|[\w\s]+\d{4})$", low, re.I) and ("amount" in low or "paid" in low or re.search(r"(dec|oct|jan)\.?\s*\d{1,2},?\s*\d{4}", low, re.I)):
            return "col_pair"
        return "data"

    @classmethod
    def _merge_nearby_words(cls, visual_row):
        if not visual_row: return []
        heights = [w.bottom - w.top for w in visual_row]
        med_h = heights[len(heights)//2] if heights else 10.0
        tol = max(4.0, 0.5 * med_h)
        merged = []
        for w in visual_row:
            if merged and w.x0 - merged[-1].x1 <= tol:
                merged[-1].text = (merged[-1].text + " " + w.text).strip()
                merged[-1].x1 = max(merged[-1].x1, w.x1)
                merged[-1].bottom = max(merged[-1].bottom, w.bottom)
            else:
                merged.append(copy.deepcopy(w))
        return merged

    @classmethod
    def _postprocess_vertical(cls, block, heading: str, is_amount_token_func, make_rows_func):
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

        for row in visual_rows:
            merged = cls._merge_nearby_words(row)
            text = " ".join(w.text for w in merged).strip()
            if not text: continue
            
            row_cls = cls._classify_vertical_row(text)
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
                if not label: continue
                
                row_dict = {"chi_tieu": label}
                if is_measure_period:
                    if current_groups: row_dict["group"] = current_groups[-1]
                    if current_periods: row_dict["period"] = current_periods[-1]
                    if amounts: row_dict["col_1"] = amounts[-1]
                    out.append(row_dict)
                elif is_comparison:
                    if current_periods: row_dict["period"] = current_periods[-1]
                    for i, a in enumerate(amounts):
                        row_dict[f"col_{i+1}"] = a
                    out.append(row_dict)

        return out if out else None

    @classmethod
    def _is_vertical_heading(cls, heading: str) -> bool:
        if not heading:
            return False
        h = heading.lower()
        hints = ("goodwill", "fixed asset", "tangible", "intangible", "finance lease",
                 "construction in progress", "depreciation", "movement", "roll")
        return any(k in h for k in hints)