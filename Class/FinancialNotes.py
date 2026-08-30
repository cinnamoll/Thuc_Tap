import re

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
            return "Không phát sinh số dư hoặc không được thuyết minh chi tiết / No outstanding balance or not disclosed."
        match = regex.search(section_text)
        return match.group(0).strip() if match else "Không có thông tin chi tiết / Information not available."

    def extract_all_to_format(self, full_text):
        if not full_text:
            return ""
        
        cleaned_text = re.sub(r'[ \t]+', ' ', full_text)
        cleaned_text = re.sub(r'\r\n', '\n', full_text)

        sec_dac_diem = self.slice_section(cleaned_text, self.sections_regex["dac_diem_hoat_dong"])
        sec_ky_ke_toan = self.slice_section(cleaned_text, self.sections_regex["ky_ke_toan_tien_te"])
        sec_chuan_muc = self.slice_section(cleaned_text, self.sections_regex["chuan_muc_che_do_ke_toan"])
        sec_chinh_sach_ke_toan = self.slice_section(cleaned_text, self.sections_regex["chinh_sach_ke_toan"])
        sec_bo_sung_balance = self.slice_section(cleaned_text, self.sections_regex["bo_sung_bang_can_doi"])
        sec_bo_sung_income = self.slice_section(cleaned_text, self.sections_regex["bo_sung_ket_qua_kinh_doanh"])
        sec_bo_sung_cashflow = self.slice_section(cleaned_text, self.sections_regex["bo_sung_luu_chuyen_tien_te"])
        sec_thong_tin_khac = self.slice_section(cleaned_text, self.sections_regex["nhung_thong_tin_khac"])

        has_non_going_concern = "không đáp ứng giả định hoạt động liên tục" in sec_chinh_sach_ke_toan.lower() or "not a going concern" in sec_chinh_sach_ke_toan.lower()
        if has_non_going_concern:
            policy_lien_tuc = re.sub(r'(?i)không\s+đáp\s+ứng\s+giả\s+định[\s\S]+', '', sec_chinh_sach_ke_toan)
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