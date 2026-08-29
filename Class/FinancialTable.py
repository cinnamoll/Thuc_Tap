import re
import pandas as pd

class FinancialTableExtractor:
    @staticmethod
    def parse_line(line):
        line = line.strip()
        if not line:
            return None

        prefix = None
        prefix_match = re.compile(r'^([A-E]|[IVX]+|\d+)\.\s+').match(line)
        if prefix_match:
            prefix = prefix_match.group(1)
            line = line[prefix_match.end():].strip()

        words = line.split()
        if not words:
            return {
                "prefix": prefix, "name": "", "code": None,
                "note_ref": None, "val1": None, "val2": None,
            }

        def is_val(w):
            return bool(re.compile(r'^(?:-|[-]?\d+(?:\.\d+)*|\(\d+(?:\.\d+)*\)|\([-]?\d+(?:\.\d+)*\))$').match(w))

        def is_code(w):
            return bool(re.compile(r'^\d{2,3}$').match(w))

        def is_note_ref(w):
            return bool(re.compile(r'^(?:\d{1,2}|[IVXivx]+\.\d+)$').match(w))

        code = None
        note_ref = None
        val2 = None
        val1 = None

        idx = len(words) - 1
        if idx >= 0 and is_val(words[idx]):
            val2 = words[idx]
            idx -= 1
            if idx >= 0 and is_val(words[idx]):
                val1 = words[idx]
                idx -= 1

        if idx >= 0 and is_code(words[idx]):
            code = words[idx]
            idx -= 1
        elif idx >= 0 and is_note_ref(words[idx]):
            pass

        if code is not None and idx >= 0 and is_note_ref(words[idx]):
            note_ref = words[idx]
            idx -= 1

        name = " ".join(words[:idx + 1])

        if val1 is None and val2 is not None:
            val1 = val2
            val2 = None

        return {
            "prefix": prefix,
            "name": name,
            "code": code,
            "note_ref": note_ref,
            "val1": val1,
            "val2": val2,
        }

    def extract_balance_sheet(self, text):
        dict_bs = {}
        current_part = None
        current_subsection = None
        subsection_rows = []
        subsection_summary = None

        def flush():
            nonlocal subsection_rows, subsection_summary
            if current_part and current_subsection:
                all_rows = subsection_rows.copy()
                if subsection_summary:
                    all_rows.append(subsection_summary)
                dict_bs[current_part][current_subsection] = pd.DataFrame(all_rows)
            subsection_rows = []
            subsection_summary = None

        lines = text.strip().split('\n')
        for line in lines:
            parsed = self.parse_line(line)
            if not parsed:
                continue

            prefix = parsed["prefix"]
            name = parsed["name"]
            code = parsed["code"]
            note_ref = parsed["note_ref"]
            val1 = parsed["val1"]
            val2 = parsed["val2"]

            if prefix in ["A", "B", "C", "D", "E"]:
                flush()
                current_part = prefix
                dict_bs[current_part] = {}
                current_subsection = None

            elif prefix and re.compile(r'^[IVX]+$').match(prefix):
                flush()
                current_subsection = prefix
                subsection_summary = {
                    "Prefix": prefix,
                    "Chỉ tiêu": name,
                    "Mã số": code if code else "",
                    "Thuyết minh": note_ref if note_ref else "",
                    "Số cuối kỳ": val1 if val1 else "",
                    "Số đầu năm": val2 if val2 else "",
                }

            elif prefix and prefix.isdigit():
                subsection_rows.append({
                    "Prefix": prefix,
                    "Chỉ tiêu": name,
                    "Mã số": code if code else "",
                    "Thuyết minh": note_ref if note_ref else "",
                    "Số cuối kỳ": val1 if val1 else "",
                    "Số đầu năm": val2 if val2 else "",
                })

        flush()
        return dict_bs

    def extract_income_statement(self, text):
        rows = []
        lines = text.strip().split('\n')
        for line in lines:
            parsed = self.parse_line(line)
            if parsed:
                rows.append({
                    "STT": parsed["prefix"] if parsed["prefix"] else "",
                    "Chỉ tiêu": parsed["name"],
                    "Mã số": parsed["code"] if parsed["code"] else "",
                    "Thuyết minh": parsed["note_ref"] if parsed["note_ref"] else "",
                    "Kỳ này": parsed["val1"] if parsed["val1"] else "",
                    "Kỳ trước": parsed["val2"] if parsed["val2"] else "",
                })
        return pd.DataFrame(rows)

    def extract_cash_flow(self, text):
        dict_cf = {}
        current_section = None
        section_rows = []
        section_summary = None

        def flush():
            nonlocal section_rows, section_summary
            if current_section:
                all_rows = section_rows.copy()
                if section_summary:
                    all_rows.append(section_summary)
                dict_cf[current_section] = pd.DataFrame(all_rows)
            section_rows = []
            section_summary = None

        lines = text.strip().split('\n')
        for line in lines:
            parsed = self.parse_line(line)
            if not parsed:
                continue

            prefix = parsed["prefix"]
            name = parsed["name"]
            code = parsed["code"]
            note_ref = parsed["note_ref"]
            val1 = parsed["val1"]
            val2 = parsed["val2"]

            if prefix and re.compile(r'^[IVX]+$').match(prefix):
                flush()
                current_section = prefix
                section_summary = {
                    "Prefix": prefix,
                    "Chỉ tiêu": name,
                    "Mã số": code if code else "",
                    "Thuyết minh": note_ref if note_ref else "",
                    "Lũy kế kỳ này": val1 if val1 else "",
                    "Lũy kế kỳ trước": val2 if val2 else "",
                }

            elif prefix and prefix.isdigit():
                section_rows.append({
                    "Prefix": prefix,
                    "Chỉ tiêu": name,
                    "Mã số": code if code else "",
                    "Thuyết minh": note_ref if note_ref else "",
                    "Lũy kế kỳ này": val1 if val1 else "",
                    "Lũy kế kỳ trước": val2 if val2 else "",
                })

            else:
                if current_section and ("thuần" in name.lower()):
                    section_summary = {
                        "Prefix": "Tổng",
                        "Chỉ tiêu": name,
                        "Mã số": code if code else "",
                        "Thuyết minh": note_ref if note_ref else "",
                        "Lũy kế kỳ này": val1 if val1 else "",
                        "Lũy kế kỳ trước": val2 if val2 else "",
                    }

        flush()
        return dict_cf