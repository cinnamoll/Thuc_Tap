import pdfplumber
from typing import Optional

from Class.ReportContent.FinancialNotesReport import FinancialNotesReport, DacDiemHoatDong, BoSungBangCanDoi, BoSungKetQuaKD, BoSungLuuChuyenTienTe, NhungThongTinKhac
from Class.NotesExtraction.SectionExtract import SectionExtractor
from Class.NotesExtraction.HeadingMapper import HeadingMapper
from Class.NotesExtraction.NotesTableExtractor import NotesTableExtractor
from Class.NotesExtraction.NotesOutlineScanner import NotesOutlineScanner

DAC_DIEM_KEY_MAP = {
    "capital_ownership": "hinh_thuc_so_huu_von",
    "form_of_ownership": "hinh_thuc_so_huu_von",
    "ownership_structure": "hinh_thuc_so_huu_von",
    "business_sector": "linh_vuc_kinh_doanh",
    "business_field": "linh_vuc_kinh_doanh",
    "principal_activities": "nganh_nghe_kinh_doanh",
    "principal_lines_of_business": "nganh_nghe_kinh_doanh",
    "business_line": "nganh_nghe_kinh_doanh",
    "operating_cycle": "chu_ky_sxkd",
    "production_cycle": "chu_ky_sxkd",
    "normal_production": "chu_ky_sxkd",
    "financial_statement_impact": "dac_diem_anh_huong_bctc",
    "operating_features": "dac_diem_anh_huong_bctc",
    "corporate_structure": "cau_truc_doanh_nghiep",
    "enterprise_structure": "cau_truc_doanh_nghiep",
    "group_structure": "cau_truc_doanh_nghiep",
    "comparability": "tuyen_bo_so_sanh",
    "statement_of_comparability": "tuyen_bo_so_sanh",
}

BO_SUNG_BCD_KEY_MAP = {
    "cash": "tien",
    "cash_and_cash_equivalents": "tien",
    "financial_investment": "dau_tu_tai_chinh",
    "investments": "dau_tu_tai_chinh",
    "trade_receivable": "phai_thu_khach_hang",
    "receivable_from_customer": "phai_thu_khach_hang",
    "prepaid_to_supplier": "tra_truoc_nguoi_ban",
    "advance_to_supplier": "tra_truoc_nguoi_ban",
    "other_receivable": "phai_thu_khac",
    "other_receivables": "phai_thu_khac",
    "asset_shortage": "tai_san_thieu_cho_xu_ly",
    "bad_debt": "no_xau",
    "doubtful_debt": "no_xau",
    "inventory": "hang_ton_kho",
    "inventories": "hang_ton_kho",
    "tangible_fixed_asset": "tang_giam_tscd_huu_hinh",
    "tangible_fixed_assets": "tang_giam_tscd_huu_hinh",
    "finance_lease": "tang_giam_tscd_thue_tai_chinh",
    "intangible_fixed_asset": "tang_giam_tscd_vo_hinh",
    "investment_property": "bat_dong_san_dau_tu",
    "construction_in_progress": "tai_san_do_dang_dai_han",
    "prepaid_expense": "chi_phi_tra_truoc",
    "prepaid_expenses": "chi_phi_tra_truoc",
    "trade_payable": "phai_tra_nguoi_ban",
    "payable_to_supplier": "phai_tra_nguoi_ban",
    "advance_from_customer": "nguoi_mua_tra_tien_truoc",
    "tax_and": "thue_va_cac_khoan_nop_nha_nuoc",
    "taxes_and": "thue_va_cac_khoan_nop_nha_nuoc",
    "tax_payable": "thue_va_cac_khoan_nop_nha_nuoc",
    "accrued_expense": "chi_phi_phai_tra",
    "accrued_expenses": "chi_phi_phai_tra",
    "unearned_revenue": "doanh_thu_chua_thuc_hien",
    "deferred_revenue": "doanh_thu_chua_thuc_hien",
    "other_payable": "phai_tra_khac",
    "other_payables": "phai_tra_khac",
    "borrowing": "vay_va_no_thue_tai_chinh",
    "borrowings": "vay_va_no_thue_tai_chinh",
    "loans": "vay_va_no_thue_tai_chinh",
    "bonds": "trai_phieu_phat_hanh",
    "provision": "du_phong_phai_tra",
    "provisions": "du_phong_phai_tra",
    "equity": "von_chu_so_huu",
    "owners_equity": "von_chu_so_huu",
    "fund": "nguon_kinh_phi",
    "off_balance": "cac_khoan_muc_ngoai_bang",
}

BO_SUNG_KQKD_KEY_MAP = {
    "gross_revenue": "tong_doanh_thu",
    "revenue_from_sales": "tong_doanh_thu",
    "sales_revenue": "tong_doanh_thu",
    "revenue_deduction": "giam_tru_doanh_thu",
    "revenue_deductions": "giam_tru_doanh_thu",
    "cost_of_sales": "gia_von_hang_ban",
    "cost_of_goods_sold": "gia_von_hang_ban",
    "financial_income": "doanh_thu_tai_chinh",
    "finance_income": "doanh_thu_tai_chinh",
    "financial_expense": "chi_phi_tai_chinh",
    "financial_expenses": "chi_phi_tai_chinh",
    "finance_expense": "chi_phi_tai_chinh",
    "selling_expense": "chi_phi_ban_hang_va_qldn",
    "selling_expenses": "chi_phi_ban_hang_va_qldn",
    "general_and_administrative": "chi_phi_ban_hang_va_qldn",
    "administrative_expense": "chi_phi_ban_hang_va_qldn",
    "operating_expense": "chi_phi_sxkd_theo_yeu_to",
    "expenses_by_nature": "chi_phi_sxkd_theo_yeu_to",
    "production_expense": "chi_phi_sxkd_theo_yeu_to",
    "other_income": "thu_nhap_khac",
    "other_expense": "chi_phi_khac",
    "other_expenses": "chi_phi_khac",
    "current_corporate_income_tax": "chi_phi_thue_tndn_hien_hanh",
    "current_income_tax": "chi_phi_thue_tndn_hien_hanh",
    "deferred_corporate_income_tax": "chi_phi_thue_tndn_hoan_lai",
    "deferred_income_tax": "chi_phi_thue_tndn_hoan_lai",
}

BO_SUNG_LCTT_KEY_MAP = {
    "non_cash": "giao_dich_khong_bang_tien",
    "restricted_cash": "tien_khong_duoc_su_dung",
    "proceeds_from_borrowing": "tien_di_vay_thuc_thu",
    "borrowing_principal": "tien_di_vay_thuc_thu",
    "repayment_of_borrowing": "tien_da_tra_goc_vay",
    "repayment_of_loans": "tien_da_tra_goc_vay",
}

NHUNG_THONG_TIN_KEY_MAP = {
    "contingent": "no_tiem_tang_cam_ket",
    "commitments": "no_tiem_tang_cam_ket",
    "subsequent_events": "su_kien_sau_ngay_ket_thuc",
    "events_after": "su_kien_sau_ngay_ket_thuc",
    "related_parties": "thong_tin_ben_lien_quan",
    "related_party": "thong_tin_ben_lien_quan",
    "segment_reporting": "bao_cao_bo_phan",
    "segment_report": "bao_cao_bo_phan",
    "comparative": "thong_tin_so_sanh",
    "comparatives": "thong_tin_so_sanh",
    "going_concern": "thong_tin_hoat_dong_lien_tuc",
    "other_information": "thong_tin_khac",
}

USE_OUTLINE_SCANNER = False

class FinancialNotesExtractor:
    def __init__(self):
        self.section_extractor = SectionExtractor()
        self.heading_mapper = HeadingMapper()
        self.table_extractor = NotesTableExtractor()

    def extract_notes_structured(self, file_path: str, page_start: int, page_end: int, year: int,
                                 scope: Optional[str] = None, period_key: Optional[str] = None) -> FinancialNotesReport:
        if USE_OUTLINE_SCANNER:
            report = self.extract_notes_structured_outline(file_path, page_start, page_end, year)
            report.scope = scope or report.scope
            report.period_key = period_key or report.period_key
            return report
        full_text = self.extract_text_from_pdf(file_path, first_page=page_start+1, last_page=page_end+1)
        raw_notes = self.section_extractor.extract_all_to_format(full_text)

        notes = FinancialNotesReport(page_start=page_start, page_end=page_end, year=year,
                                     scope=scope, period_key=period_key)
        notes.raw_data = raw_notes

        KEY_MAP = [
            ("dac_diem_hoat_dong", lambda k: any(term in k for term in ["đặc điểm hoạt động", "principal activities", "operating features", "corporate structure"])),
            ("ky_ke_toan_tien_te", lambda k: any(term in k for term in ["kỳ kế toán", "accounting period", "monetary unit"])),
            ("chuan_muc_che_do", lambda k: any(term in k for term in ["chuẩn mực", "accounting standard", "accounting regime"])),
            ("chinh_sach_hoat_dong_lien_tuc", lambda k: ("hoạt động liên tục" in k or "going concern" in k) and "không" not in k and "not" not in k),
            ("chinh_sach_khong_lien_tuc", lambda k: "không đáp ứng" in k or "không liên tục" in k or "not a going concern" in k),
            ("bo_sung_bang_can_doi", lambda k: "bảng cân đối" in k or "balance sheet" in k or "financial position" in k),
            ("bo_sung_ket_qua_kd", lambda k: "kết quả" in k or "income statement" in k or "profit or loss" in k),
            ("bo_sung_luu_chuyen_tien_te", lambda k: "lưu chuyển tiền tệ" in k or "cash flow" in k),
            ("nhung_thong_tin_khac", lambda k: "thông tin khác" in k or "những thông tin" in k or "other information" in k),
        ]

        sub_map_config = {
            "dac_diem_hoat_dong": (DacDiemHoatDong, DAC_DIEM_KEY_MAP),
            "bo_sung_bang_can_doi": (BoSungBangCanDoi, BO_SUNG_BCD_KEY_MAP),
            "bo_sung_ket_qua_kd": (BoSungKetQuaKD, BO_SUNG_KQKD_KEY_MAP),
            "bo_sung_luu_chuyen_tien_te": (BoSungLuuChuyenTienTe, BO_SUNG_LCTT_KEY_MAP),
            "nhung_thong_tin_khac": (NhungThongTinKhac, NHUNG_THONG_TIN_KEY_MAP),
        }

        for section in raw_notes:
            if not isinstance(section, dict):
                continue
            for key, value in section.items():
                kl = key.lower()
                for field_name, matcher in KEY_MAP:
                    if matcher(kl):
                        if field_name in sub_map_config and isinstance(value, dict):
                            model_cls, key_map = sub_map_config[field_name]
                            mapped = {}
                            for match_term, en_field in key_map.items():
                                for k, v in value.items():
                                    if match_term.lower() in k.lower():
                                        mapped[en_field] = str(v) if v else None
                                        break
                            setattr(notes, field_name, model_cls(**mapped))
                        else:
                            setattr(notes, field_name, str(value) if value else None)
                        break

        text_sections = self.section_extractor.slice_by_numeric_sections(full_text)
        tables, page_headings, table_metadata = self.table_extractor.extract_tables_from_pages(file_path, page_start, page_end)

        if not tables:
            merged_tables: dict = {}
        else:
            merged_tables = dict(tables)

        clean_tables = {}
        for heading, rows in merged_tables.items():
            if isinstance(rows, list) and rows and isinstance(rows[0], dict) and "text" not in rows[0]:
                clean_tables[heading] = rows

        for heading, text in text_sections.items():
            if not text:
                continue
            if heading in merged_tables:
                continue
            if not self.heading_mapper.is_valid_section_key(heading):
                continue
            merged_tables[heading] = [{"text": text}]

        if table_metadata:
            notes.table_metadata = table_metadata

        sub_model_cls_map = {
            "bo_sung_bang_can_doi": BoSungBangCanDoi,
            "bo_sung_ket_qua_kd": BoSungKetQuaKD,
            "bo_sung_luu_chuyen_tien_te": BoSungLuuChuyenTienTe,
            "nhung_thong_tin_khac": NhungThongTinKhac,
        }

        for heading, rows in merged_tables.items():
            if not rows or not isinstance(rows, list):
                continue
            if isinstance(rows[0], dict) and set(rows[0].keys()) == {"text"}:
                continue
            
            section_field = self.heading_mapper.map_heading_to_section(heading)
            renamed_rows = self.table_extractor.rename_notes_columns(rows, heading)

            sub_key = self.heading_mapper.map_heading_to_sub_key(heading)
            target_cls = sub_model_cls_map.get(section_field, BoSungBangCanDoi)

            current_sub = getattr(notes, section_field, None)
            if current_sub is None:
                current_sub = target_cls()
            elif isinstance(current_sub, str):
                current_sub = target_cls(thong_tin_khac=current_sub)

            if not hasattr(current_sub, sub_key):
                sub_key = "thong_tin_khac"

            existing_val = getattr(current_sub, sub_key, None)
            if isinstance(existing_val, list):
                existing_val.extend(renamed_rows)
                setattr(current_sub, sub_key, existing_val)
            else:
                setattr(current_sub, sub_key, renamed_rows)

            setattr(notes, section_field, current_sub)

        return notes

    def extract_notes_structured_outline(self, file_path: str, page_start: int, page_end: int, year: int) -> FinancialNotesReport:
        scanner = NotesOutlineScanner()
        spans = scanner.scan(file_path, page_start, page_end)
        segments = scanner.to_segments(spans)

        notes = FinancialNotesReport(page_start=page_start, page_end=page_end, year=year)
        sub_models = {
            "bo_sung_bang_can_doi": BoSungBangCanDoi,
            "bo_sung_ket_qua_kd": BoSungKetQuaKD,
            "bo_sung_luu_chuyen_tien_te": BoSungLuuChuyenTienTe,
            "nhung_thong_tin_khac": NhungThongTinKhac,
        }

        for field, subs in segments.items():
            if field in sub_models:
                model_cls = sub_models[field]
                allowed = set(model_cls.model_fields) if hasattr(model_cls, "model_fields") else set()
                payload = {k: v for k, v in subs.items() if v and (not allowed or k in allowed)}
                setattr(notes, field, model_cls(**payload))
            else:
                setattr(notes, field, subs.get("text") or None)

        notes.table_metadata = {
            s.heading: {
                "target_field": s.section_field or "",
                "sub_key": s.binding.sub_key if s.binding else "",
                "matched_by": s.binding.matched_by if s.binding else "section",
                "table_shape": s.binding.table_shape if s.binding else "narrative",
            }
            for s in spans
        }
        notes.raw_data = segments
        return notes

    def extract_text_from_pdf(self, file_path: str, first_page=None, last_page=None) -> str:
        text_parts = []
        with pdfplumber.open(file_path) as pdf:
            start_page = (first_page - 1) if first_page else 0
            end_page = last_page if last_page else len(pdf.pages)
            end_page = min(end_page, len(pdf.pages))

            for page_num in range(start_page, end_page):
                page = pdf.pages[page_num]
                page_text = page.extract_text(x_tolerance=30, layout=True)
                if page_text and page_text.strip():
                    text_parts.append(page_text)

        return "\n\n".join(text_parts)