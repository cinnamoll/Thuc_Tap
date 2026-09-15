import re
from typing import Any, Dict, List, Optional, Tuple, Type
from pydantic import BaseModel
from dataclasses import dataclass

from Class.ReportContent.FinancialNotesReport import DacDiemHoatDong, BoSungBangCanDoi, BoSungKetQuaKD, BoSungLuuChuyenTienTe,NhungThongTinKhac,FinancialNotesReport

@dataclass
class BindingResult:
    field: str
    sub_key: str
    model_cls: Type[BaseModel]
    table_shape: str
    matched_by: str
    note_no: Optional[str] = None
    raw_heading: Optional[str] = None
    page_num: Optional[int] = None

@dataclass
class NoteBindingDefinition:
    note_no: str
    field: str
    sub_key: str
    model_cls: Type[BaseModel]
    table_shape: str
    keywords: Tuple[str, ...]

@dataclass
class KeywordFallbackRule:
    patterns: Tuple[str, ...]
    field: str
    sub_key: str
    model_cls: Type[BaseModel]
    table_shape: str

NOTES_COL_MAPS: Dict[str, Dict[str, str]] = {
    "movement": {
        "period_current": "beginning_balance",
        "period_prior": "increase",
        "accum_current": "decrease",
        "accum_prior": "ending_balance",
        "col_1": "beginning_balance",
        "col_2": "increase",
        "col_3": "decrease",
        "col_4": "ending_balance",
    },
    "comparison": {
        "period_current": "current_year",
        "period_prior": "prior_year",
        "col_1": "current_year",
        "col_2": "prior_year",
    },
    "loan": {
        "period_current": "outstanding_balance",
        "period_prior": "interest_rate",
        "accum_current": "maturity",
        "accum_prior": "collateral",
        "col_1": "outstanding_balance",
        "col_2": "interest_rate",
        "col_3": "maturity",
        "col_4": "collateral",
    },
}

_D = DacDiemHoatDong
_B = BoSungBangCanDoi
_K = BoSungKetQuaKD
_C = BoSungLuuChuyenTienTe
_N = NhungThongTinKhac
_F = FinancialNotesReport
NB = NoteBindingDefinition
FR = KeywordFallbackRule

CIRCULAR_200_BINDING_TABLE: Dict[str, NoteBindingDefinition] = {
    # I - Enterprise characteristics
    "1": NB("1", "dac_diem_hoat_dong", "hinh_thuc_so_huu_von", _D, "narrative", ("form of ownership", "hình thức sở hữu", "business")),
    "I": NB("I", "dac_diem_hoat_dong", "hinh_thuc_so_huu_von", _D, "narrative", ("characteristics", "đặc điểm hoạt động")),
    "1.1": NB("1.1", "dac_diem_hoat_dong", "hinh_thuc_so_huu_von", _D, "narrative", ("form of ownership", "hình thức sở hữu")),
    "1.2": NB("1.2", "dac_diem_hoat_dong", "linh_vuc_kinh_doanh", _D, "narrative", ("business field", "lĩnh vực")),
    "1.3": NB("1.3", "dac_diem_hoat_dong", "nganh_nghe_kinh_doanh", _D, "narrative", ("business lines", "ngành nghề")),
    "1.4": NB("1.4", "dac_diem_hoat_dong", "chu_ky_sxkd", _D, "narrative", ("operating cycle", "chu kỳ")),
    "1.5": NB("1.5", "dac_diem_hoat_dong", "dac_diem_anh_huong_bctc", _D, "narrative", ("affecting", "ảnh hưởng")),
    "1.6": NB("1.6", "dac_diem_hoat_dong", "cau_truc_doanh_nghiep", _D, "narrative", ("subsidiaries", "cấu trúc", "công ty con")),
    "1.7": NB("1.7", "dac_diem_hoat_dong", "tuyen_bo_so_sanh", _D, "narrative", ("comparability", "so sánh")),
    # II / III - Accounting policies
    "2": NB("2", "ky_ke_toan_tien_te", "ky_ke_toan_tien_te", _F, "narrative", ("accounting period", "kỳ kế toán")),
    "II": NB("II", "ky_ke_toan_tien_te", "ky_ke_toan_tien_te", _F, "narrative", ("accounting period", "kỳ kế toán")),
    "2.1": NB("2.1", "ky_ke_toan_tien_te", "ky_ke_toan_tien_te", _F, "narrative", ("accounting period", "kỳ kế toán")),
    "2.2": NB("2.2", "ky_ke_toan_tien_te", "ky_ke_toan_tien_te", _F, "narrative", ("currency", "đơn vị tiền tệ")),
    "2.3": NB("2.3", "chuan_muc_che_do", "chuan_muc_che_do", _F, "narrative", ("accounting system", "chuẩn mực")),
    "III": NB("III", "chuan_muc_che_do", "chuan_muc_che_do", _F, "narrative", ("accounting standard", "chuẩn mực")),
    "IV": NB("IV", "chinh_sach_hoat_dong_lien_tuc", "chinh_sach_hoat_dong_lien_tuc", _F, "narrative", ("accounting policies", "chính sách")),
    # Balance Sheet notes
    "3": NB("3", "bo_sung_bang_can_doi", "tien", _B, "comparison", ("cash", "tiền")),
    "V.1": NB("V.1", "bo_sung_bang_can_doi", "tien", _B, "comparison", ("cash", "tiền")),
    "4": NB("4", "bo_sung_bang_can_doi", "dau_tu_tai_chinh", _B, "comparison", ("investment", "đầu tư")),
    "4.1": NB("4.1", "bo_sung_bang_can_doi", "dau_tu_tai_chinh", _B, "comparison", ("held-to-maturity", "nắm giữ")),
    "4.2": NB("4.2", "bo_sung_bang_can_doi", "dau_tu_tai_chinh", _B, "comparison", ("other entities", "đơn vị khác")),
    "V.2": NB("V.2", "bo_sung_bang_can_doi", "dau_tu_tai_chinh", _B, "comparison", ("investment", "đầu tư")),
    "5": NB("5", "bo_sung_bang_can_doi", "phai_thu_khach_hang", _B, "comparison", ("receivable", "phải thu")),
    "V.3": NB("V.3", "bo_sung_bang_can_doi", "phai_thu_khach_hang", _B, "comparison", ("receivable", "phải thu")),
    "6": NB("6", "bo_sung_bang_can_doi", "tra_truoc_nguoi_ban", _B, "comparison", ("prepaid to supplier", "advance", "trả trước")),
    "V.4": NB("V.4", "bo_sung_bang_can_doi", "tra_truoc_nguoi_ban", _B, "comparison", ("prepaid", "trả trước")),
    "7": NB("7", "bo_sung_bang_can_doi", "phai_thu_khac", _B, "comparison", ("loan receivable", "phải thu")),
    "8": NB("8", "bo_sung_bang_can_doi", "phai_thu_khac", _B, "comparison", ("other receivable", "phải thu khác")),
    "V.5": NB("V.5", "bo_sung_bang_can_doi", "phai_thu_khac", _B, "comparison", ("other receivable", "phải thu khác")),
    "9": NB("9", "bo_sung_bang_can_doi", "no_xau", _B, "comparison", ("bad debt", "doubtful", "nợ xấu")),
    "V.6": NB("V.6", "bo_sung_bang_can_doi", "no_xau", _B, "comparison", ("doubtful", "nợ xấu")),
    "10": NB("10", "bo_sung_bang_can_doi", "chi_phi_tra_truoc", _B, "comparison", ("prepaid", "chi phí trả trước")),
    "V.13": NB("V.13", "bo_sung_bang_can_doi", "chi_phi_tra_truoc", _B, "comparison", ("prepaid", "chi phí trả trước")),
    "11": NB("11", "bo_sung_bang_can_doi", "hang_ton_kho", _B, "comparison", ("inventor", "hàng tồn kho")),
    "V.7": NB("V.7", "bo_sung_bang_can_doi", "hang_ton_kho", _B, "comparison", ("inventor", "hàng tồn kho")),
    "12": NB("12", "bo_sung_bang_can_doi", "tang_giam_tscd_huu_hinh", _B, "movement", ("tangible", "hữu hình")),
    "V.8": NB("V.8", "bo_sung_bang_can_doi", "tang_giam_tscd_huu_hinh", _B, "movement", ("tangible", "hữu hình")),
    "13": NB("13", "bo_sung_bang_can_doi", "tang_giam_tscd_thue_tai_chinh", _B, "movement", ("finance lease", "thuê tài chính")),
    "V.9": NB("V.9", "bo_sung_bang_can_doi", "tang_giam_tscd_thue_tai_chinh", _B, "movement", ("finance lease", "thuê tài chính")),
    "14": NB("14", "bo_sung_bang_can_doi", "tai_san_do_dang_dai_han", _B, "comparison", ("construction in progress", "dở dang")),
    "V.12": NB("V.12", "bo_sung_bang_can_doi", "tai_san_do_dang_dai_han", _B, "comparison", ("construction", "dở dang")),
    "15": NB("15", "bo_sung_bang_can_doi", "tang_giam_tscd_vo_hinh", _B, "movement", ("intangible", "vô hình")),
    "V.10": NB("V.10", "bo_sung_bang_can_doi", "tang_giam_tscd_vo_hinh", _B, "movement", ("intangible", "vô hình")),
    "V.11": NB("V.11", "bo_sung_bang_can_doi", "bat_dong_san_dau_tu", _B, "movement", ("investment property", "bất động sản đầu tư")),
    "16": NB("16", "bo_sung_bang_can_doi", "phai_tra_nguoi_ban", _B, "comparison", ("trade payable", "phải trả người bán")),
    "V.15": NB("V.15", "bo_sung_bang_can_doi", "phai_tra_nguoi_ban", _B, "comparison", ("payable", "phải trả")),
    "17": NB("17", "bo_sung_bang_can_doi", "nguoi_mua_tra_tien_truoc", _B, "comparison", ("advance from customer", "người mua trả tiền trước")),
    "V.16": NB("V.16", "bo_sung_bang_can_doi", "nguoi_mua_tra_tien_truoc", _B, "comparison", ("advance", "trả trước")),
    "18": NB("18", "bo_sung_bang_can_doi", "thue_va_cac_khoan_nop_nha_nuoc", _B, "comparison", ("tax", "thuế")),
    "V.17": NB("V.17", "bo_sung_bang_can_doi", "thue_va_cac_khoan_nop_nha_nuoc", _B, "comparison", ("tax", "thuế")),
    "V.18": NB("V.18", "bo_sung_bang_can_doi", "chi_phi_phai_tra", _B, "comparison", ("accrued", "chi phí phải trả")),
    "19": NB("19", "bo_sung_bang_can_doi", "doanh_thu_chua_thuc_hien", _B, "comparison", ("unearned", "deferred revenue", "chưa thực hiện")),
    "V.19": NB("V.19", "bo_sung_bang_can_doi", "doanh_thu_chua_thuc_hien", _B, "comparison", ("unearned", "chưa thực hiện")),
    "20": NB("20", "bo_sung_bang_can_doi", "phai_tra_khac", _B, "comparison", ("other payable", "phải trả khác")),
    "V.20": NB("V.20", "bo_sung_bang_can_doi", "phai_tra_khac", _B, "comparison", ("other payable", "phải trả khác")),
    "21": NB("21", "bo_sung_bang_can_doi", "vay_va_no_thue_tai_chinh", _B, "loan", ("borrowing", "loan", "vay")),
    "21.1": NB("21.1", "bo_sung_bang_can_doi", "vay_va_no_thue_tai_chinh", _B, "loan", ("short-term loan", "vay ngắn hạn")),
    "21.2": NB("21.2", "bo_sung_bang_can_doi", "vay_va_no_thue_tai_chinh", _B, "loan", ("long-term loan", "vay dài hạn")),
    "V.21": NB("V.21", "bo_sung_bang_can_doi", "vay_va_no_thue_tai_chinh", _B, "loan", ("borrowing", "loan", "vay")),
    "V.22": NB("V.22", "bo_sung_bang_can_doi", "trai_phieu_phat_hanh", _B, "loan", ("bond", "trái phiếu")),
    "22": NB("22", "bo_sung_bang_can_doi", "von_chu_so_huu", _B, "movement", ("equity", "vốn chủ sở hữu")),
    "V.23": NB("V.23", "bo_sung_bang_can_doi", "von_chu_so_huu", _B, "movement", ("equity", "vốn chủ sở hữu")),
    "23": NB("23", "bo_sung_bang_can_doi", "cac_khoan_muc_ngoai_bang", _B, "comparison", ("off balance", "ngoại bảng")),
    "V.25": NB("V.25", "bo_sung_bang_can_doi", "cac_khoan_muc_ngoai_bang", _B, "comparison", ("off balance", "ngoại bảng")),
    # Income Statement notes
    "24": NB("24", "bo_sung_ket_qua_kd", "tong_doanh_thu", _K, "comparison", ("revenue", "doanh thu")),
    "VI.1": NB("VI.1", "bo_sung_ket_qua_kd", "tong_doanh_thu", _K, "comparison", ("revenue", "doanh thu")),
    "25": NB("25", "bo_sung_ket_qua_kd", "giam_tru_doanh_thu", _K, "comparison", ("deduction", "giảm trừ")),
    "VI.2": NB("VI.2", "bo_sung_ket_qua_kd", "giam_tru_doanh_thu", _K, "comparison", ("deduction", "giảm trừ")),
    "26": NB("26", "bo_sung_ket_qua_kd", "gia_von_hang_ban", _K, "comparison", ("cost of sales", "cost of goods", "giá vốn")),
    "VI.3": NB("VI.3", "bo_sung_ket_qua_kd", "gia_von_hang_ban", _K, "comparison", ("cost of sales", "giá vốn")),
    "27": NB("27", "bo_sung_ket_qua_kd", "doanh_thu_tai_chinh", _K, "comparison", ("financial income", "doanh thu tài chính")),
    "VI.4": NB("VI.4", "bo_sung_ket_qua_kd", "doanh_thu_tai_chinh", _K, "comparison", ("financial income", "doanh thu tài chính")),
    "28": NB("28", "bo_sung_ket_qua_kd", "chi_phi_tai_chinh", _K, "comparison", ("financial expense", "chi phí tài chính")),
    "VI.5": NB("VI.5", "bo_sung_ket_qua_kd", "chi_phi_tai_chinh", _K, "comparison", ("financial expense", "chi phí tài chính")),
    "29": NB("29", "bo_sung_ket_qua_kd", "chi_phi_ban_hang_va_qldn", _K, "comparison", ("selling", "bán hàng")),
    "30": NB("30", "bo_sung_ket_qua_kd", "chi_phi_ban_hang_va_qldn", _K, "comparison", ("general", "administrative", "quản lý")),
    "VI.6": NB("VI.6", "bo_sung_ket_qua_kd", "chi_phi_ban_hang_va_qldn", _K, "comparison", ("selling", "administrative", "bán hàng", "quản lý")),
    "VI.7": NB("VI.7", "bo_sung_ket_qua_kd", "chi_phi_sxkd_theo_yeu_to", _K, "comparison", ("by element", "by nature", "yếu tố")),
    "31": NB("31", "bo_sung_ket_qua_kd", "thu_nhap_khac", _K, "comparison", ("other income", "thu nhập khác")),
    "VI.8": NB("VI.8", "bo_sung_ket_qua_kd", "thu_nhap_khac", _K, "comparison", ("other income", "thu nhập khác")),
    "32": NB("32", "bo_sung_ket_qua_kd", "chi_phi_khac", _K, "comparison", ("other expense", "chi phí khác")),
    "VI.9": NB("VI.9", "bo_sung_ket_qua_kd", "chi_phi_khac", _K, "comparison", ("other expense", "chi phí khác")),
    "33": NB("33", "bo_sung_ket_qua_kd", "chi_phi_thue_tndn_hien_hanh", _K, "comparison", ("corporate income tax", "thuế tndn")),
    "VI.10": NB("VI.10", "bo_sung_ket_qua_kd", "chi_phi_thue_tndn_hien_hanh", _K, "comparison", ("current tax", "thuế hiện hành")),
    "VI.11": NB("VI.11", "bo_sung_ket_qua_kd", "chi_phi_thue_tndn_hoan_lai", _K, "comparison", ("deferred tax", "thuế hoãn lại")),
    # Cash Flow notes
    "34": NB("34", "bo_sung_luu_chuyen_tien_te", "thong_tin_khac", _C, "comparison", ("cash flows", "lưu chuyển tiền")),
    "VII.1": NB("VII.1", "bo_sung_luu_chuyen_tien_te", "giao_dich_khong_bang_tien", _C, "comparison", ("non-cash", "phi tiền tệ")),
    "VII.2": NB("VII.2", "bo_sung_luu_chuyen_tien_te", "tien_khong_duoc_su_dung", _C, "comparison", ("restricted cash", "hạn chế sử dụng")),
    "VII.3": NB("VII.3", "bo_sung_luu_chuyen_tien_te", "tien_di_vay_thuc_thu", _C, "comparison", ("proceeds from borrowing", "tiền đi vay")),
    "VII.4": NB("VII.4", "bo_sung_luu_chuyen_tien_te", "tien_da_tra_goc_vay", _C, "comparison", ("repayment of borrowing", "trả gốc vay")),
    # Other information
    "35": NB("35", "nhung_thong_tin_khac", "thong_tin_ben_lien_quan", _N, "comparison", ("related part", "bên liên quan")),
    "36": NB("36", "nhung_thong_tin_khac", "su_kien_sau_ngay_ket_thuc", _N, "narrative", ("subsequent", "events after", "sau ngày kết thúc")),
    "37": NB("37", "nhung_thong_tin_khac", "bao_cao_bo_phan", _N, "comparison", ("segment", "bộ phận")),
    "38": NB("38", "nhung_thong_tin_khac", "thong_tin_khac", _N, "comparison", ("fair value", "rủi ro", "khác")),
    "VIII.1": NB("VIII.1", "nhung_thong_tin_khac", "no_tiem_tang_cam_ket", _N, "narrative", ("contingent", "tiềm tàng")),
    "VIII.2": NB("VIII.2", "nhung_thong_tin_khac", "su_kien_sau_ngay_ket_thuc", _N, "narrative", ("events after", "sau ngày kết thúc")),
    "VIII.3": NB("VIII.3", "nhung_thong_tin_khac", "thong_tin_ben_lien_quan", _N, "comparison", ("related part", "bên liên quan")),
    "VIII.4": NB("VIII.4", "nhung_thong_tin_khac", "bao_cao_bo_phan", _N, "comparison", ("segment", "bộ phận")),
    "VIII.5": NB("VIII.5", "nhung_thong_tin_khac", "thong_tin_so_sanh", _N, "narrative", ("comparative", "so sánh")),
    "VIII.6": NB("VIII.6", "nhung_thong_tin_khac", "thong_tin_hoat_dong_lien_tuc", _N, "narrative", ("going concern", "liên tục")),
}

FALLBACK_KEYWORD_RULES: List[KeywordFallbackRule] = [
    # Balance Sheet notes
    FR(("cash", "tiền và tương đương", "tiền"), "bo_sung_bang_can_doi", "tien", _B, "comparison"),
    FR(("held-to-maturity", "financial investment", "đầu tư tài chính", "chứng khoán"), "bo_sung_bang_can_doi", "dau_tu_tai_chinh", _B, "comparison"),
    FR(("trade receivable", "receivable from customer", "phải thu của khách hàng", "phải thu khách hàng"), "bo_sung_bang_can_doi", "phai_thu_khach_hang", _B, "comparison"),
    FR(("advance to supplier", "prepayment to supplier", "prepaid to supplier", "trả trước cho người bán"), "bo_sung_bang_can_doi", "tra_truoc_nguoi_ban", _B, "comparison"),
    FR(("other receivable", "phải thu khác"), "bo_sung_bang_can_doi", "phai_thu_khac", _B, "comparison"),
    FR(("asset awaiting resolution", "tài sản thiếu"), "bo_sung_bang_can_doi", "tai_san_thieu_cho_xu_ly", _B, "comparison"),
    FR(("bad debt", "doubtful debt", "nợ xấu"), "bo_sung_bang_can_doi", "no_xau", _B, "comparison"),
    FR(("inventor", "hàng tồn kho"), "bo_sung_bang_can_doi", "hang_ton_kho", _B, "comparison"),
    FR(("tangible fixed", "tài sản cố định hữu hình"), "bo_sung_bang_can_doi", "tang_giam_tscd_huu_hinh", _B, "movement"),
    FR(("finance lease fixed", "thuê tài chính"), "bo_sung_bang_can_doi", "tang_giam_tscd_thue_tai_chinh", _B, "movement"),
    FR(("intangible fixed", "tài sản cố định vô hình"), "bo_sung_bang_can_doi", "tang_giam_tscd_vo_hinh", _B, "movement"),
    FR(("investment property", "bất động sản đầu tư"), "bo_sung_bang_can_doi", "bat_dong_san_dau_tu", _B, "movement"),
    FR(("construction in progress", "xây dựng cơ bản dở dang", "dở dang"), "bo_sung_bang_can_doi", "tai_san_do_dang_dai_han", _B, "comparison"),
    FR(("prepaid expense", "chi phí trả trước"), "bo_sung_bang_can_doi", "chi_phi_tra_truoc", _B, "comparison"),
    FR(("trade payable", "payable to supplier", "phải trả người bán"), "bo_sung_bang_can_doi", "phai_tra_nguoi_ban", _B, "comparison"),
    FR(("advance from customer", "người mua trả tiền trước"), "bo_sung_bang_can_doi", "nguoi_mua_tra_tien_truoc", _B, "comparison"),
    FR(("taxes and", "tax payable", "thuế và các khoản"), "bo_sung_bang_can_doi", "thue_va_cac_khoan_nop_nha_nuoc", _B, "comparison"),
    FR(("accrued expense", "chi phí phải trả"), "bo_sung_bang_can_doi", "chi_phi_phai_tra", _B, "comparison"),
    FR(("unearned revenue", "deferred revenue", "doanh thu chưa thực hiện"), "bo_sung_bang_can_doi", "doanh_thu_chua_thuc_hien", _B, "comparison"),
    FR(("other payable", "phải trả khác"), "bo_sung_bang_can_doi", "phai_tra_khac", _B, "comparison"),
    FR(("borrowing", "loan", "vay và nợ"), "bo_sung_bang_can_doi", "vay_va_no_thue_tai_chinh", _B, "loan"),
    FR(("bond", "trái phiếu"), "bo_sung_bang_can_doi", "trai_phieu_phat_hanh", _B, "loan"),
    FR(("provision", "dự phòng phải trả"), "bo_sung_bang_can_doi", "du_phong_phai_tra", _B, "movement"),
    FR(("owner's equity", "owners' equity", "shareholders' equity", "vốn chủ sở hữu"), "bo_sung_bang_can_doi", "von_chu_so_huu", _B, "movement"),
    FR(("off balance", "ngoại bảng"), "bo_sung_bang_can_doi", "cac_khoan_muc_ngoai_bang", _B, "comparison"),
    # Income Statement notes
    FR(("revenue from sales", "gross revenue", "sales revenue", "doanh thu bán hàng"), "bo_sung_ket_qua_kd", "tong_doanh_thu", _K, "comparison"),
    FR(("revenue deduction", "giảm trừ doanh thu"), "bo_sung_ket_qua_kd", "giam_tru_doanh_thu", _K, "comparison"),
    FR(("cost of sales", "cost of goods", "giá vốn hàng bán"), "bo_sung_ket_qua_kd", "gia_von_hang_ban", _K, "comparison"),
    FR(("financial income", "finance income", "doanh thu hoạt động tài chính"), "bo_sung_ket_qua_kd", "doanh_thu_tai_chinh", _K, "comparison"),
    FR(("financial expense", "finance expense", "chi phí tài chính"), "bo_sung_ket_qua_kd", "chi_phi_tai_chinh", _K, "comparison"),
    FR(("selling expense", "general and administrative", "chi phí bán hàng", "chi phí quản lý"), "bo_sung_ket_qua_kd", "chi_phi_ban_hang_va_qldn", _K, "comparison"),
    FR(("expenses by nature", "by element", "theo yếu tố"), "bo_sung_ket_qua_kd", "chi_phi_sxkd_theo_yeu_to", _K, "comparison"),
    FR(("other income", "thu nhập khác"), "bo_sung_ket_qua_kd", "thu_nhap_khac", _K, "comparison"),
    FR(("other expense", "chi phí khác"), "bo_sung_ket_qua_kd", "chi_phi_khac", _K, "comparison"),
    FR(("current corporate income tax", "current income tax", "thuế tndn hiện hành"), "bo_sung_ket_qua_kd", "chi_phi_thue_tndn_hien_hanh", _K, "comparison"),
    FR(("deferred corporate income tax", "deferred income tax", "thuế tndn hoãn lại"), "bo_sung_ket_qua_kd", "chi_phi_thue_tndn_hoan_lai", _K, "comparison"),
    # Cash Flow notes
    FR(("non-cash", "phi tiền tệ"), "bo_sung_luu_chuyen_tien_te", "giao_dich_khong_bang_tien", _C, "comparison"),
    FR(("restricted cash", "hạn chế sử dụng"), "bo_sung_luu_chuyen_tien_te", "tien_khong_duoc_su_dung", _C, "comparison"),
    FR(("proceeds from borrowing", "tiền thu từ đi vay"), "bo_sung_luu_chuyen_tien_te", "tien_di_vay_thuc_thu", _C, "comparison"),
    FR(("repayment of borrowing", "tiền trả nợ gốc"), "bo_sung_luu_chuyen_tien_te", "tien_da_tra_goc_vay", _C, "comparison"),
    # Cash Flow notes -- English-only variant wording (annual-report phrasing)
    FR(("not used", "không sử dụng", "không dùng"), "bo_sung_luu_chuyen_tien_te", "tien_khong_duoc_su_dung", _C, "comparison"),
    FR(("borrowings received", "loans received", "tiền đi vay thực thu"), "bo_sung_luu_chuyen_tien_te", "tien_di_vay_thuc_thu", _C, "comparison"),
    FR(("repayment of loan", "repayment of principal", "loan principal", "trả gốc vay", "trả nợ gốc"), "bo_sung_luu_chuyen_tien_te", "tien_da_tra_goc_vay", _C, "comparison"),
    # Other information notes
    FR(("contingent", "commitment", "nợ tiềm tàng", "cam kết"), "nhung_thong_tin_khac", "no_tiem_tang_cam_ket", _N, "narrative"),
    FR(("subsequent event", "events after", "sau ngày kết thúc"), "nhung_thong_tin_khac", "su_kien_sau_ngay_ket_thuc", _N, "narrative"),
    FR(("related part", "bên liên quan"), "nhung_thong_tin_khac", "thong_tin_ben_lien_quan", _N, "comparison"),
    FR(("segment", "bộ phận"), "nhung_thong_tin_khac", "bao_cao_bo_phan", _N, "comparison"),
    FR(("comparative", "so sánh"), "nhung_thong_tin_khac", "thong_tin_so_sanh", _N, "narrative"),
    FR(("going concern", "hoạt động liên tục"), "nhung_thong_tin_khac", "thong_tin_hoat_dong_lien_tuc", _N, "narrative"),
]

def parse_note_address(heading: str) -> Optional[str]:
    if not heading:
        return None
    h = heading.strip()

    m_roman = re.match(r"(?i)^(VIII|VII|VI|IV|V|III|II|I)\.(\d{1,2})", h)
    if m_roman:
        return f"{m_roman.group(1).upper()}.{int(m_roman.group(2))}"

    m_dec = re.match(r"^(\d{1,2})\.(\d{1,2})\b", h)
    if m_dec:
        return f"{int(m_dec.group(1))}.{int(m_dec.group(2))}"

    m_int = re.match(r"^(\d{1,2})[\s.:]", h)
    if m_int:
        return str(int(m_int.group(1)))
    return None

def resolve_binding(heading: str, page_num: Optional[int] = None) -> BindingResult:
    """Resolve a clean heading string to its target Pydantic field and sub_key.

    Order: exact address lookup -> shared keyword fallback -> unmatched.
    """
    if not heading or not heading.strip():
        return BindingResult(
            field="nhung_thong_tin_khac",
            sub_key="thong_tin_khac",
            model_cls=_N,
            table_shape="comparison",
            matched_by="unmatched",
            raw_heading=heading,
            page_num=page_num,
        )

    h_clean = heading.strip()
    h_low = h_clean.lower()
    address = parse_note_address(h_clean)

    if address and address in CIRCULAR_200_BINDING_TABLE:
        defn = CIRCULAR_200_BINDING_TABLE[address]
        title_conflict = False
        if defn.keywords:
            has_keyword_match = any(kw in h_low for kw in defn.keywords)
            if not has_keyword_match and len(h_low.split()) >= 3:
                for rule in FALLBACK_KEYWORD_RULES:
                    if any(p in h_low for p in rule.patterns) and rule.sub_key != defn.sub_key:
                        title_conflict = True
                        break
        if not title_conflict:
            return BindingResult(
                field=defn.field,
                sub_key=defn.sub_key,
                model_cls=defn.model_cls,
                table_shape=defn.table_shape,
                matched_by="exact",
                note_no=address,
                raw_heading=heading,
                page_num=page_num,
            )

    for rule in FALLBACK_KEYWORD_RULES:
        if any(p in h_low for p in rule.patterns):
            return BindingResult(
                field=rule.field,
                sub_key=rule.sub_key,
                model_cls=rule.model_cls,
                table_shape=rule.table_shape,
                matched_by="keyword_fallback",
                note_no=address,
                raw_heading=heading,
                page_num=page_num,
            )

    return BindingResult(
        field="nhung_thong_tin_khac",
        sub_key="thong_tin_khac",
        model_cls=_N,
        table_shape="comparison",
        matched_by="unmatched",
        note_no=address,
        raw_heading=heading,
        page_num=page_num,
    )

def is_amount_token(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    if re.fullmatch(r"\d{1,3}([.,]\d{1,3})?%", t):
        return True
    digits = re.sub(r"[%,.() -]", "", t)
    return digits.isdigit() and len(digits) >= 3

def merge_multiline_header(cells_rows: List[List[str]]) -> List[List[str]]:
    if len(cells_rows) < 2:
        return cells_rows

    header_block = []
    i = 0
    while i < len(cells_rows) and not any(is_amount_token(c) for c in cells_rows[i]):
        header_block.append(cells_rows[i])
        i += 1
        if len(header_block) >= 4:
            break

    if len(header_block) <= 1:
        return cells_rows

    ncols = max(len(r) for r in header_block)
    merged_header = []
    for c in range(ncols):
        parts = [r[c].strip() for r in header_block if c < len(r) and r[c].strip()]
        merged_header.append(" ".join(parts))

    return [merged_header] + cells_rows[i:]

def remap_notes_columns(rows: List[Dict[str, Any]], heading: str, table_shape: Optional[str] = None) -> List[Dict[str, Any]]:
    if not rows:
        return rows

    shape = table_shape or resolve_binding(heading).table_shape
    col_map = NOTES_COL_MAPS.get(shape, NOTES_COL_MAPS["comparison"])

    renamed_rows = []
    for row in rows:
        new_row: Dict[str, Any] = {}
        for k, v in row.items():
            if k == "chi_tieu":
                new_row["title"] = v
            elif k in col_map:
                new_row[col_map[k]] = v
            elif k == "col_1":
                new_row["current_period"] = v
            elif k == "col_2":
                new_row["previous_period"] = v
            elif k.startswith("col_"):
                new_row[f"period_{k[4:]}"] = v
            else:
                new_row[k] = v
        renamed_rows.append(new_row)

    return renamed_rows

def resolve_binding_scoped(title: str, section_field: Optional[str] = None, addr: Optional[str] = None, page_num: Optional[int] = None) -> BindingResult:
    h = (title or "").strip()
    h_low = h.lower()

    if section_field:
        if addr:
            defn = CIRCULAR_200_BINDING_TABLE.get(addr)
            if defn is not None and defn.field == section_field:
                if not defn.keywords or any(k in h_low for k in defn.keywords):
                    return BindingResult(
                        field=defn.field, sub_key=defn.sub_key, model_cls=defn.model_cls,
                        table_shape=defn.table_shape, matched_by="exact",
                        note_no=addr, raw_heading=title, page_num=page_num)
        for rule in FALLBACK_KEYWORD_RULES:
            if rule.field == section_field and any(p in h_low for p in rule.patterns):
                return BindingResult(
                    field=rule.field, sub_key=rule.sub_key, model_cls=rule.model_cls,
                    table_shape=rule.table_shape, matched_by="keyword_fallback",
                    note_no=addr, raw_heading=title, page_num=page_num)
        model_cls = next(
            (d.model_cls for d in CIRCULAR_200_BINDING_TABLE.values()
             if d.field == section_field), _N)
        return BindingResult(
            field=section_field, sub_key="thong_tin_khac", model_cls=model_cls,
            table_shape="comparison", matched_by="unmatched",
            note_no=addr, raw_heading=title, page_num=page_num)

    return resolve_binding(f"{addr} {h}".strip() if addr else h, page_num)