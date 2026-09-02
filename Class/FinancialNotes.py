import re
import pdfplumber
import pytesseract
from pdf2image import convert_from_path
from collections import Counter

from Class.TableExtractor import TableExtractor, Word
from Class.ReportContent.FinancialNotesReport import FinancialNotesReport

class FinancialNotesExtractor:
    sections_regex = {
        "dac_diem_hoat_dong": re.compile(
            r"(?i)(?:(?:I|1)\.?\s+)?(?:CHARACTERISTICS\s+OF\s+(?:BUSINESS\s+ACTIVITIES|THE\s+STATED\s+ENTERPRISE|THE\s+ENTERPRISE))[\s\S]*?(?=(?:(?:II|2)\.?\s+)?(?:ACCOUNTING\s+PERIOD))"
        ),
        "ky_ke_toan_tien_te": re.compile(
            r"(?i)(?:(?:II|2)\.?\s+)?(?:ACCOUNTING\s+PERIOD[,\s]+CURRENCY\s+UNIT)[\s\S]*?(?=(?:(?:III|3)\.?\s+)?(?:ACCOUNTING\s+SYSTEM|ACCOUNTING\s+STANDARDS))"
        ),
        "chuan_muc_che_do_ke_toan": re.compile(
            r"(?i)(?:(?:III|3)\.?\s+)?(?:ACCOUNTING\s+SYSTEM|ACCOUNTING\s+STANDARDS)[\s\S]*?(?=(?:(?:IV|4)\.?\s+)?(?:SUMMARY\s+OF\s+SIGNIFICANT\s+ACCOUNTING\s+POLICIES|SUMMARY\s+OF\s+ACCOUNTING\s+POLICIES))"
        ),
        "chinh_sach_ke_toan": re.compile(
            r"(?i)(?:(?:IV|4)\.?\s+)?(?:SUMMARY\s+OF\s+SIGNIFICANT\s+ACCOUNTING\s+POLICIES|SUMMARY\s+OF\s+ACCOUNTING\s+POLICIES)[\s\S]*?(?=(?:(?:V|5)\.?\s+)?(?:ADDITIONAL\s+INFORMATION\s+FOR\s+ITEMS\s+SHOWN\s+IN\s+THE))"
        ),
        "bo_sung_bang_can_doi": re.compile(
            r"(?i)(?:(?:V|5)\.?\s+)?(?:ADDITIONAL\s+INFORMATION\s+FOR\s+ITEMS\s+SHOWN\s+IN\s+THE\s+(?:CONSOLIDATED\s+|SEPARATE\s+)?BALANCE\s+SHEET)[\s\S]*?(?=(?:(?:VI|6)\.?\s+)?(?:ADDITIONAL\s+INFORMATION\s+FOR\s+ITEMS\s+SHOWN\s+IN\s+THE\s+(?:CONSOLIDATED\s+|SEPARATE\s+)?(?:INCOME\s+STATEMENT|BUSINESS\s+PERFORMANCE\s+REPORT)))"
        ),
        "bo_sung_ket_qua_kinh_doanh": re.compile(
            r"(?i)(?:(?:VI|6)\.?\s+)?(?:ADDITIONAL\s+INFORMATION\s+FOR\s+ITEMS\s+SHOWN\s+IN\s+THE\s+(?:CONSOLIDATED\s+|SEPARATE\s+)?(?:INCOME\s+STATEMENT|BUSINESS\s+PERFORMANCE\s+REPORT))[\s\S]*?(?=(?:(?:VII|7)\.?\s+)?(?:ADDITIONAL\s+INFORMATION\s+FOR\s+ITEMS\s+SHOWN\s+IN\s+THE\s+(?:CONSOLIDATED\s+|SEPARATE\s+)?CASH\s+FLOWS?\s+STATEMENT))"
        ),
        "bo_sung_luu_chuyen_tien_te": re.compile(
            r"(?i)(?:(?:VII|7)\.?\s+)?(?:ADDITIONAL\s+INFORMATION\s+FOR\s+ITEMS\s+SHOWN\s+IN\s+THE\s+(?:CONSOLIDATED\s+|SEPARATE\s+)?CASH\s+FLOWS?\s+STATEMENT)[\s\S]*?(?=(?:(?:VIII|8)\.?\s+)?(?:OTHER\s+INFORMATION))"
        ),
        "nhung_thong_tin_khac": re.compile(
            r"(?i)(?:(?:VIII|8)\.?\s+)?(?:OTHER\s+INFORMATION)[\s\S]+?(?=(?:Prepared\s+by|Chief\s+Accountant|General\s+Director|Approved\s+by)|$)"
        ),
    }

    sub_regex_dac_diem_hoat_dong = {
        "hinh_thuc_so_huu_von": re.compile(
            r"(?i)(?:Form\s+of\s+ownership|Capital\s+ownership)[\s\S]*?(?=(?:Business\s+fields|Business\s+lines|Normal\s+production))"
        ),
        "linh_vuc_kinh_doanh": re.compile(
            r"(?i)(?:Business\s+fields|Business\s+activity)[\s\S]*?(?=(?:Business\s+lines|Normal\s+production))"
        ),
        "nganh_nghe_kinh_doanh": re.compile(
            r"(?i)(?:Business\s+lines|Principal\s+activities)[\s\S]*?(?=(?:Normal\s+production|Operating\s+cycle))"
        ),
        "chu_ky_sxkd_thong_thuong": re.compile(
            r"(?i)(?:Normal\s+production\s+and\s+business\s+cycle|Operating\s+cycle)[\s\S]*?(?=(?:Corporate\s+structure|Operating\s+features))"
        ),
        "dac_diem_anh_huong_bctc": re.compile(
            r"(?i)(?:Operating\s+features\s+affecting\s+the\s+financial\s+statements)[\s\S]*?(?=(?:Corporate\s+structure|Subsidiaries))"
        ),
        "cau_truc_doanh_nghiep": re.compile(
            r"(?i)(?:Corporate\s+structure|List\s+of\s+subsidiaries|Subsidiaries)[\s\S]*?(?=(?:Statement\s+on\s+comparability|Comparability\s+of\s+information|$))"
        ),
        "tuyen_bo_so_sanh_thong_tin": re.compile(
            r"(?i)(?:Statement\s+on\s+comparability|Comparability\s+of\s+information)[\s\S]+?$"
        ),
    }

    sub_regex_bo_sung_bang_can_doi = {
        "tien": re.compile(
            r"(?i)(?:\b\d+\.?\s+)?(?:Cash\s+and\s+cash\s+equivalents)[\s\S]*?(?=(?:\b\d+\.?\s+)?(?:Financial\s+investments))"
        ),
        "dau_tu_tai_chinh": re.compile(
            r"(?i)(?:\b\d+\.?\s+)?(?:Financial\s+investments)[\s\S]*?(?=(?:\b\d+\.?\s+)?(?:Trade\s+receivables))"
        ),
        "phai_thu_khach_hang": re.compile(
            r"(?i)(?:\b\d+\.?\s+)?(?:Trade\s+receivables|Short-term\s+trade\s+receivables)[\s\S]*?(?=(?:\b\d+\.?\s+)?(?:Other\s+receivables))"
        ),
        "phai_thu_khac": re.compile(
            r"(?i)(?:\b\d+\.?\s+)?(?:Other\s+receivables)[\s\S]*?(?=(?:\b\d+\.?\s+)?(?:Inventories))"
        ),
        "tai_san_thieu_cho_xu_ly": re.compile(
            r"(?i)(?:\b\d+\.?\s+)?(?:Assets\s+awaiting\s+resolution)[\s\S]*?(?=(?:\b\d+\.?\s+)?(?:Doubtful\s+debts|Bad\s+debts))"
        ),
        "no_xau": re.compile(
            r"(?i)(?:\b\d+\.?\s+)?(?:Doubtful\s+debts|Bad\s+debts)[\s\S]*?(?=(?:\b\d+\.?\s+)?(?:Inventories))"
        ),
        "hang_ton_kho": re.compile(
            r"(?i)(?:\b\d+\.?\s+)?(?:Inventories)[\s\S]*?(?=(?:\b\d+\.?\s+)?(?:Tangible\s+fixed\s+assets|Fixed\s+assets))"
        ),
        "tang_giam_tscd_huu_hinh": re.compile(
            r"(?i)(?:\b\d+\.?\s+)?(?:Tangible\s+fixed\s+assets)[\s\S]*?(?=(?:\b\d+\.?\s+)?(?:Loans\s+and\s+finance\s+lease\s+liabilities))"
        ),
        "vay_va_no_thue_tai_chinh": re.compile(
            r"(?i)(?:\b\d+\.?\s+)?(?:Loans\s+and\s+finance\s+lease\s+liabilities)[\s\S]+?$"
        ),
    }

    sub_regex_nhung_thong_tin_khac = {
        "no_tiem_tang_cam_ket": re.compile(
            r"(?i)(?:Contingent\s+liabilities\s+and\s+commitments|Contingent\s+liabilities)[\s\S]*?(?=(?:Events\s+after\s+the\s+reporting\s+period|Events\s+after\s+the\s+balance\s+sheet\s+date))"
        ),
        "su_kien_sau_ngay_ket_thuc": re.compile(
            r"(?i)(?:Events\s+after\s+the\s+reporting\s+period|Events\s+after\s+the\s+balance\s+sheet\s+date)[\s\S]*?(?=(?:Transactions\s+and\s+balances\s+with\s+related\s+parties|Related\s+parties))"
        ),
        "ben_lien_quan": re.compile(
            r"(?i)(?:Transactions\s+and\s+balances\s+with\s+related\s+parties|Related\s+parties)[\s\S]*?(?=(?:Segment\s+reporting))"
        ),
        "bao_cao_bo_phan": re.compile(
            r"(?i)(?:Segment\s+reporting)[\s\S]*?(?=(?:Comparative\s+figures|Comparative\s+information))"
        ),
        "thong_tin_so_sanh": re.compile(
            r"(?i)(?:Comparative\s+figures|Comparative\s+information)[\s\S]*?(?=(?:Going\s+concern\s+assumption|Going\s+concern))"
        ),
        "thong_tin_hoat_dong_lien_tuc": re.compile(
            r"(?i)(?:Going\s+concern\s+assumption|Going\s+concern)[\s\S]*?(?=(?:Other\s+information|$))"
        ),
        "thong_tin_khac_bo_sung": re.compile(
            r"(?i)(?:Other\s+information)[\s\S]+?$"
        ),
    }

    def slice_section(self, full_text, regex):
        match = regex.search(full_text)
        return match.group(0) if match else ""

    def slice_sub_section(self, section_text, regex):
        if not section_text:
            return "Không phát sinh số dư hoặc không được Notes chi tiết / No outstanding balance or not disclosed."
        match = regex.search(section_text)
        return match.group(0).strip() if match else "Không có thông tin chi tiết / Information not available."

    def extract_all_to_format(self, full_text):
        if not full_text:
            return ""

        cleaned_text = re.sub(r'[ \t]+', ' ', full_text)
        cleaned_text = re.sub(r'\r\n', '\n', cleaned_text)

        sec_dac_diem = self.slice_section(cleaned_text, self.sections_regex["dac_diem_hoat_dong"])
        sec_ky_ke_toan = self.slice_section(cleaned_text, self.sections_regex["ky_ke_toan_tien_te"])
        sec_chuan_muc = self.slice_section(cleaned_text, self.sections_regex["chuan_muc_che_do_ke_toan"])
        sec_chinh_sach_ke_toan = self.slice_section(cleaned_text, self.sections_regex["chinh_sach_ke_toan"])
        sec_bo_sung_balance = self.slice_section(cleaned_text, self.sections_regex["bo_sung_bang_can_doi"])
        sec_bo_sung_income = self.slice_section(cleaned_text, self.sections_regex["bo_sung_ket_qua_kinh_doanh"])
        sec_bo_sung_cashflow = self.slice_section(cleaned_text, self.sections_regex["bo_sung_luu_chuyen_tien_te"])
        sec_thong_tin_khac = self.slice_section(cleaned_text, self.sections_regex["nhung_thong_tin_khac"])

        has_non_going_concern = "not a going concern" in sec_chinh_sach_ke_toan.lower()
        if has_non_going_concern:
            policy_lien_tuc = re.sub(r'(?i)not\s+a\s+going\s+concern[\s\S]+', '', sec_chinh_sach_ke_toan)
            policy_khong_lien_tuc = sec_chinh_sach_ke_toan[len(policy_lien_tuc):]
        else:
            policy_lien_tuc = sec_chinh_sach_ke_toan if sec_chinh_sach_ke_toan else "Không có thông tin / Not available."
            policy_khong_lien_tuc = "Không áp dụng. Doanh nghiệp vẫn đang đáp ứng giả định hoạt động liên tục. / Not applicable. The enterprise meets the going concern assumption."

        formatted_output = [
            {
                "Đặc điểm hoạt động của doanh nghiệp": {
                    "Hình thức sở hữu vốn": self.slice_sub_section(sec_dac_diem, self.sub_regex_dac_diem_hoat_dong["hinh_thuc_so_huu_von"]),
                    "Lĩnh vực kinh doanh": self.slice_sub_section(sec_dac_diem, self.sub_regex_dac_diem_hoat_dong["linh_vuc_kinh_doanh"]),
                    "Ngành nghề kinh doanh": self.slice_sub_section(sec_dac_diem, self.sub_regex_dac_diem_hoat_dong["nganh_nghe_kinh_doanh"]),
                    "Chu kỳ sản xuất, kinh doanh thông thường": self.slice_sub_section(sec_dac_diem, self.sub_regex_dac_diem_hoat_dong["chu_ky_sxkd_thong_thuong"]),
                    "Đặc điểm hoạt động của doanh nghiệp trong năm tài chính có ảnh hưởng đến báo cáo tài chính": self.slice_sub_section(sec_dac_diem, self.sub_regex_dac_diem_hoat_dong["dac_diem_anh_huong_bctc"]),
                    "Cấu trúc doanh nghiệp": self.slice_sub_section(sec_dac_diem, self.sub_regex_dac_diem_hoat_dong["cau_truc_doanh_nghiep"]),
                    "Tuyên bố về khả năng so sánh thông tin trên Báo cáo tài chính": self.slice_sub_section(sec_dac_diem, self.sub_regex_dac_diem_hoat_dong["tuyen_bo_so_sanh_thong_tin"])
                }
            },
            {
                "Kỳ kế toán, đơn vị tiền tệ sử dụng trong kế toán": sec_ky_ke_toan if sec_ky_ke_toan else "Không tìm thấy thông tin / Not found."
            },
            {
                "Chuẩn mực và chế độ kế toán áp dụng": sec_chuan_muc if sec_chuan_muc else "Không tìm thấy thông tin / Not found."
            },
            {
                "Các chính sách kế toán áp dụng trong trường hợp doanh nghiệp hoạt động liên tục": policy_lien_tuc
            },
            {
                "Các chính sách kế toán áp dụng (trong trường hợp doanh nghiệp không đáp ứng giả định hoạt động liên tục)": policy_khong_lien_tuc
            },
            {
                "Thông tin bổ sung cho các khoản mục trình bày trong Bảng cân đối kế toán": {
                    "Tiền": self.slice_sub_section(sec_bo_sung_balance, self.sub_regex_bo_sung_bang_can_doi["tien"]),
                    "Các khoản đầu tư tài chính": self.slice_sub_section(sec_bo_sung_balance, self.sub_regex_bo_sung_bang_can_doi["dau_tu_tai_chinh"]),
                    "Phải thu của khách hàng": self.slice_sub_section(sec_bo_sung_balance, self.sub_regex_bo_sung_bang_can_doi["phai_thu_khach_hang"]),
                    "Phải thu khác": self.slice_sub_section(sec_bo_sung_balance, self.sub_regex_bo_sung_bang_can_doi["phai_thu_khac"]),
                    "Tài sản thiếu chờ xử lý": self.slice_sub_section(sec_bo_sung_balance, self.sub_regex_bo_sung_bang_can_doi["tai_san_thieu_cho_xu_ly"]),
                    "Nợ xấu": self.slice_sub_section(sec_bo_sung_balance, self.sub_regex_bo_sung_bang_can_doi["no_xau"]),
                    "Hàng tồn kho": self.slice_sub_section(sec_bo_sung_balance, self.sub_regex_bo_sung_bang_can_doi["hang_ton_kho"]),
                    "Tăng, giảm tài sản cố định hữu hình": self.slice_sub_section(sec_bo_sung_balance, self.sub_regex_bo_sung_bang_can_doi["tang_giam_tscd_huu_hinh"]),
                    "Vay và nợ thuê tài chính thuê tài chính": self.slice_sub_section(sec_bo_sung_balance, self.sub_regex_bo_sung_bang_can_doi["vay_va_no_thue_tai_chinh"])
                }
            },
            {
                "Thông tin bổ sung cho các khoản mục trình bày trong Báo cáo kết quả hoạt động kinh doanh": sec_bo_sung_income if sec_bo_sung_income else "Không tìm thấy thông tin / Not found."
            },
            {
                "Thông tin bổ sung cho các khoản mục trình bày trong báo cáo lưu chuyển tiền tệ": sec_bo_sung_cashflow if sec_bo_sung_cashflow else "Không tìm thấy thông tin / Not found."
            },
            {
                "Những thông tin khác": {
                    "Những khoản nợ tiềm tàng, khoản cam kết và những thông tin tài chính khác": self.slice_sub_section(sec_thong_tin_khac, self.sub_regex_nhung_thong_tin_khac["no_tiem_tang_cam_ket"]),
                    "Những sự kiện phát sinh sau ngày kết thúc kỳ kế toán năm": self.slice_sub_section(sec_thong_tin_khac, self.sub_regex_nhung_thong_tin_khac["su_kien_sau_ngay_ket_thuc"]),
                    "Thông tin về các bên liên quan": self.slice_sub_section(sec_thong_tin_khac, self.sub_regex_nhung_thong_tin_khac["ben_lien_quan"]),
                    "Trình bày tài sản, doanh thu, kết quả kinh doanh theo bộ phận": self.slice_sub_section(sec_thong_tin_khac, self.sub_regex_nhung_thong_tin_khac["bao_cao_bo_phan"]),
                    "Thông tin so sánh": self.slice_sub_section(sec_thong_tin_khac, self.sub_regex_nhung_thong_tin_khac["thong_tin_so_sanh"]),
                    "Thông tin về hoạt động liên tục": self.slice_sub_section(sec_thong_tin_khac, self.sub_regex_nhung_thong_tin_khac["thong_tin_hoat_dong_lien_tuc"]),
                    "Những thông tin khác": self.slice_sub_section(sec_thong_tin_khac, self.sub_regex_nhung_thong_tin_khac["thong_tin_khac_bo_sung"])
                }
            }
        ]

        return formatted_output
    
    SECTION_NO = re.compile(r"^(\d{1,2}(?:\.\d+)?)\s+(.+)$")
    NUMBER_FORMAT = re.compile(r"^\d{1,2}(\.\d+)?$")
    SECTION_HEADER_RE = re.compile(r"^(\d{1,2}(?:\.\d+)?)\s+(.+)$", re.MULTILINE)
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
        (["contingent", "commitment", "related part", "segment", "subsequent", "event after", "events since", "going concern", "comparative",],
            "nhung_thong_tin_khac",
        ),
    ]

    def map_heading_to_section(self, heading: str) -> str:
        h = heading.lower()
        for keywords, section_key in self.HEADING_TO_SECTION:
            if any(kw in h for kw in keywords):
                return section_key
        return "bo_sung_bang_can_doi"

    @staticmethod
    def build_notes_row(cleaned:dict) -> dict:
        row = {
            "Items": cleaned.get("chi_tieu", ""),
        }
        reserved = {"chi_tieu"}
        for k, v in cleaned.items():
            if k not in reserved:
                row[k] = v
        return row
    
    @staticmethod
    def parse_section_key(heading: str) -> tuple:
        m = re.compile(r"^(\d{1,2}(?:\.\d+)?)").match(heading)
        if not m:
            return (999, 0)
        parts = m.group(1).split(".")
        major = int(parts[0])
        minor = int(parts[1]) if len(parts) > 1 else 0
        return (major, minor)

    @staticmethod
    def is_valid_section_key(key: str) -> bool:
        if len(key) > 80:
            return False
        if re.compile(r"^\d{1,2}(?:\.\d+)?\s+\d+(\s+\d+)*$").match(key.strip()):
            return False

        prefix_m = re.match(r"^\d{1,2}(?:\.\d+)?\s*", key)
        suffix = key[prefix_m.end():].strip() if prefix_m else key
        if suffix:
            non_word = re.sub(r"[\w\s]", "", suffix)   
            ratio = len(non_word) / len(suffix)
            if ratio >= 0.25:
                return False
            if not re.search(r"[A-Za-z]{2,}", suffix):
                return False
        return True
    
    @staticmethod
    def extract_tables_from_pages(file_path: str, page_start: int, page_end: int, dpi: int = 400) -> dict[str, list[dict]]:
        te = TableExtractor()
        te.dpi = dpi
        result: dict[str, list[dict]] = {}

        with pdfplumber.open(file_path) as pdf:
            imgs = convert_from_path(file_path, dpi=dpi, first_page=page_start + 1, last_page=min(page_end + 1, len(pdf.pages)))
            for idx, page_num in enumerate(range(page_start, page_end + 1)):
                if idx >= len(imgs):
                    break
                page = pdf.pages[page_num]
                w_pt, h_pt = float(page.width), float(page.height)

                ocr_data = pytesseract.image_to_data(
                    imgs[idx], output_type=pytesseract.Output.DICT,
                )
                img_w, img_h = imgs[idx].size
                sx, sy = w_pt / img_w, h_pt / img_h

                tagged_words: list[tuple[Word, tuple]] = []
                for j in range(len(ocr_data["text"])):
                    text = ocr_data["text"][j].strip()
                    conf = (int(ocr_data["conf"][j]) if ocr_data["conf"][j] not in ("-1", "") else -1)
                    if not text or conf < 10:
                        continue
                    x = ocr_data["left"][j] * sx
                    y = ocr_data["top"][j] * sy
                    w_px = ocr_data["width"][j] * sx
                    h_px = ocr_data["height"][j] * sy
                    line_key = (
                        ocr_data["block_num"][j],
                        ocr_data["par_num"][j],
                        ocr_data["line_num"][j],
                    )
                    tagged_words.append(
                        (Word(text, x, x + w_px, y, y + h_px), line_key)
                    )

                if not tagged_words:
                    continue

                words = [tw[0] for tw in tagged_words]
                ocr_lines = te.group_into_lines_ocr(tagged_words)

                has_any_fin = any(
                    te.is_financial_number(w.text) for w in words
                )
                if not has_any_fin:
                    continue

                segments: list[tuple[str, list[list[Word]]]] = []
                current_heading = ""
                current_table_lines: list[list[Word]] = []

                for line in ocr_lines:
                    line_text = " ".join(w.text for w in line).strip()
                    has_fin = any(te.is_financial_number(w.text) for w in line)

                    if has_fin:
                        current_table_lines.append(line)
                    else:
                        if line_text:
                            m_num = FinancialNotesExtractor.SECTION_NO.match(line_text)
                            is_num_format = FinancialNotesExtractor.NUMBER_FORMAT.match(line_text)
                            is_heading_part = current_heading and FinancialNotesExtractor.NUMBER_FORMAT.match(current_heading)
                            
                            if m_num or is_num_format or is_heading_part:
                                if current_table_lines:
                                    segments.append((current_heading, current_table_lines))
                                    current_table_lines = []

                                if m_num or is_num_format:
                                    current_heading = line_text
                                else:
                                    current_heading = current_heading + " " + line_text if current_heading else line_text
                            else:
                                if current_table_lines:
                                    current_table_lines.append(line)
                                else:
                                    current_heading = (current_heading + " " + line_text).strip() if current_heading else line_text

                if current_table_lines:
                    segments.append((current_heading, current_table_lines))
                for heading, table_lines in segments:
                    if not table_lines:
                        continue
                    rows = te.words_to_rows_with_lines(
                        table_lines, words, w_pt,
                    )
                    extracted = []
                    for r in rows:
                        c = te.clean_row(r)
                        if not c.get("chi_tieu"):
                            continue
                        extracted.append(FinancialNotesExtractor.build_notes_row(c))
                    if not extracted:
                        continue
                    key = heading if heading else f"Untitled_p{page_num}"
                    if key in result:
                        result[key].extend(extracted)
                    else:
                        result[key] = extracted

        return result

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

    def slice_by_numeric_sections(self, full_text: str) -> dict:
        matches = list(self.SECTION_HEADER_RE.finditer(full_text))

        result = {}
        best_len = {}
        for i, m in enumerate(matches):
                num_part = m.group(1)
                title_part = m.group(2).strip()
                heading = f"{num_part} {title_part}"

                if not self.is_valid_section_key(heading):
                    continue
                start = m.end()
                end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
                content = full_text[start:end].strip()

                key = self.parse_section_key(heading)
                if key in best_len and len(content) <= best_len[key][1]:
                    continue 
                if key in best_len:
                    del result[best_len[key][0]]
                best_len[key] = (heading, len(content))
                result[heading] = content
        return result

    def extract_notes_structured(self, file_path: str, page_start: int, page_end: int, year: int):
        texts = []
        with pdfplumber.open(file_path) as pdf:
            imgs = convert_from_path(file_path, first_page=page_start + 1, last_page=min(page_end + 1, len(pdf.pages)), dpi=400)
            for i, page_num in enumerate(range(page_start, page_end + 1)):
                if i >= len(imgs):
                    break
                page = pdf.pages[page_num]
                text = page.extract_text() or ""
                if text.strip():
                    texts.append(text)
                else:
                    ocr_text = pytesseract.image_to_string(imgs[i], lang="eng")
                    texts.append(ocr_text)
        full_text = "\n".join(texts)
        raw_notes = self.extract_all_to_format(full_text)

        notes = FinancialNotesReport(page_start=page_start, page_end=page_end, year=year)
        notes.raw_data = raw_notes

        KEY_MAP = [
            ("dac_diem_hoat_dong", lambda k: "đặc điểm hoạt động" in k),
            ("ky_ke_toan_tien_te", lambda k: "kỳ kế toán" in k),
            ("chuan_muc_che_do", lambda k: "chuẩn mực" in k),
            ("chinh_sach_hoat_dong_lien_tuc", lambda k: "hoạt động liên tục" in k and "không" not in k),
            ("chinh_sach_khong_lien_tuc", lambda k: "không đáp ứng" in k or "không liên tục" in k),
            ("bo_sung_bang_can_doi", lambda k: "bảng cân đối" in k),
            ("bo_sung_ket_qua_kd", lambda k: "kết quả" in k),
            ("bo_sung_luu_chuyen_tien_te", lambda k: "lưu chuyển tiền tệ" in k),
            ("nhung_thong_tin_khac", lambda k: "thông tin khác" in k or "những thông tin" in k),
        ]

        for section in raw_notes:
            if not isinstance(section, dict):
                continue
            for key, value in section.items():
                kl = key.lower()
                for field_name, matcher in KEY_MAP:
                    if matcher(kl):
                        if field_name in ("dac_diem_hoat_dong", "bo_sung_bang_can_doi", "nhung_thong_tin_khac"):
                            setattr(notes, field_name, value if isinstance(value, dict) else {"noi_dung": str(value)})
                        else:
                            setattr(notes, field_name, str(value) if value else None)
                        break
        cleaned_text = re.sub(r'[ \t]+', ' ', full_text)
        cleaned_text = re.sub(r'\r\n', '\n', cleaned_text)
        text_sections = self.slice_by_numeric_sections(cleaned_text)
        tables = FinancialNotesExtractor.extract_tables_from_pages(file_path, page_start, page_end)

        all_sections = {}
        table_keys = {self.parse_section_key(h) for h in tables}
        for heading, text in text_sections.items():
            if self.parse_section_key(heading) not in table_keys:
                all_sections[heading] = [{"text": text}]

        if tables:
            notes.tables = tables
            for heading, rows in tables.items():
                m = self.SECTION_NO.match(heading)
                section_num = m.group(1) if m else ""
                section_field = self.map_heading_to_section(section_num)
                renamed_rows = self.rename_notes_columns(rows, heading)
                all_sections[heading] = renamed_rows

                current = getattr(notes, section_field, None)
                if current is None:
                    current = {}
                if not isinstance(current, dict):
                    current = {"noi_dung": str(current)}
                if heading in current and isinstance(current[heading], list):
                    current[heading].extend(renamed_rows)
                else:
                    current[heading] = renamed_rows
                setattr(notes, section_field, current)

        notes.sections = all_sections if all_sections else None
        return notes