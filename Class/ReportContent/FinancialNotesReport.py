from pydantic import BaseModel
from typing import Optional, Dict, List, Any, Union

class DacDiemHoatDong(BaseModel):
    hinh_thuc_so_huu_von: Optional[str] = None
    linh_vuc_kinh_doanh: Optional[str] = None
    nganh_nghe_kinh_doanh: Optional[str] = None
    chu_ky_sxkd: Optional[str] = None
    dac_diem_anh_huong_bctc: Optional[str] = None
    cau_truc_doanh_nghiep: Optional[str] = None
    tuyen_bo_so_sanh: Optional[str] = None
    model_config = {"arbitrary_types_allowed": True}

class BoSungBangCanDoi(BaseModel):
    tien: Optional[Union[str, List[dict]]] = None
    dau_tu_tai_chinh: Optional[Union[str, List[dict]]] = None
    phai_thu_khach_hang: Optional[Union[str, List[dict]]] = None
    tra_truoc_nguoi_ban: Optional[Union[str, List[dict]]] = None
    phai_thu_khac: Optional[Union[str, List[dict]]] = None
    tai_san_thieu_cho_xu_ly: Optional[Union[str, List[dict]]] = None
    no_xau: Optional[Union[str, List[dict]]] = None
    hang_ton_kho: Optional[Union[str, List[dict]]] = None
    tang_giam_tscd_huu_hinh: Optional[Union[str, List[dict]]] = None
    tang_giam_tscd_thue_tai_chinh: Optional[Union[str, List[dict]]] = None
    tang_giam_tscd_vo_hinh: Optional[Union[str, List[dict]]] = None
    bat_dong_san_dau_tu: Optional[Union[str, List[dict]]] = None
    tai_san_do_dang_dai_han: Optional[Union[str, List[dict]]] = None
    chi_phi_tra_truoc: Optional[Union[str, List[dict]]] = None
    phai_tra_nguoi_ban: Optional[Union[str, List[dict]]] = None
    nguoi_mua_tra_tien_truoc: Optional[Union[str, List[dict]]] = None
    thue_va_cac_khoan_nop_nha_nuoc: Optional[Union[str, List[dict]]] = None
    chi_phi_phai_tra: Optional[Union[str, List[dict]]] = None
    doanh_thu_chua_thuc_hien: Optional[Union[str, List[dict]]] = None
    phai_tra_khac: Optional[Union[str, List[dict]]] = None
    vay_va_no_thue_tai_chinh: Optional[Union[str, List[dict]]] = None
    trai_phieu_phat_hanh: Optional[Union[str, List[dict]]] = None
    du_phong_phai_tra: Optional[Union[str, List[dict]]] = None
    von_chu_so_huu: Optional[Union[str, List[dict]]] = None
    nguon_kinh_phi: Optional[Union[str, List[dict]]] = None
    cac_khoan_muc_ngoai_bang: Optional[Union[str, List[dict]]] = None
    thong_tin_khac: Optional[Union[str, List[dict]]] = None
    model_config = {"arbitrary_types_allowed": True}

class BoSungKetQuaKD(BaseModel):
    tong_doanh_thu: Optional[Union[str, List[dict]]] = None
    giam_tru_doanh_thu: Optional[Union[str, List[dict]]] = None
    gia_von_hang_ban: Optional[Union[str, List[dict]]] = None
    doanh_thu_tai_chinh: Optional[Union[str, List[dict]]] = None
    chi_phi_tai_chinh: Optional[Union[str, List[dict]]] = None
    chi_phi_ban_hang_va_qldn: Optional[Union[str, List[dict]]] = None
    chi_phi_sxkd_theo_yeu_to: Optional[Union[str, List[dict]]] = None
    thu_nhap_khac: Optional[Union[str, List[dict]]] = None
    chi_phi_khac: Optional[Union[str, List[dict]]] = None
    chi_phi_thue_tndn_hien_hanh: Optional[Union[str, List[dict]]] = None
    chi_phi_thue_tndn_hoan_lai: Optional[Union[str, List[dict]]] = None
    thong_tin_khac: Optional[Union[str, List[dict]]] = None
    model_config = {"arbitrary_types_allowed": True}

class BoSungLuuChuyenTienTe(BaseModel):
    giao_dich_khong_bang_tien: Optional[Union[str, List[dict]]] = None
    tien_khong_duoc_su_dung: Optional[Union[str, List[dict]]] = None
    tien_di_vay_thuc_thu: Optional[Union[str, List[dict]]] = None
    tien_da_tra_goc_vay: Optional[Union[str, List[dict]]] = None
    thong_tin_khac: Optional[Union[str, List[dict]]] = None
    model_config = {"arbitrary_types_allowed": True}

class NhungThongTinKhac(BaseModel):
    no_tiem_tang_cam_ket: Optional[Union[str, List[dict]]] = None
    su_kien_sau_ngay_ket_thuc: Optional[Union[str, List[dict]]] = None
    thong_tin_ben_lien_quan: Optional[Union[str, List[dict]]] = None
    bao_cao_bo_phan: Optional[Union[str, List[dict]]] = None
    thong_tin_so_sanh: Optional[Union[str, List[dict]]] = None
    thong_tin_hoat_dong_lien_tuc: Optional[Union[str, List[dict]]] = None
    thong_tin_khac: Optional[Union[str, List[dict]]] = None
    model_config = {"arbitrary_types_allowed": True}

class FinancialNotesReport(BaseModel):
    page_start: int = 0
    page_end: int = 0

    year: Optional[int] = None
    scope: Optional[str] = None
    period_key: Optional[str] = None

    dac_diem_hoat_dong: Optional[DacDiemHoatDong] = None
    ky_ke_toan_tien_te: Optional[str] = None
    chuan_muc_che_do: Optional[str] = None
    chinh_sach_hoat_dong_lien_tuc: Optional[str] = None
    chinh_sach_khong_lien_tuc: Optional[str] = None

    bo_sung_bang_can_doi: Optional[BoSungBangCanDoi] = None
    bo_sung_ket_qua_kd: Optional[BoSungKetQuaKD] = None
    bo_sung_luu_chuyen_tien_te: Optional[BoSungLuuChuyenTienTe] = None
    nhung_thong_tin_khac: Optional[NhungThongTinKhac] = None

    table_metadata: Optional[Dict[str, Dict[str, str]]] = None
    raw_data: Optional[Any] = None
    model_config = {"arbitrary_types_allowed": True}

    def has_going_concern_warning(self) -> bool:
        if self.chinh_sach_khong_lien_tuc:
            text = self.chinh_sach_khong_lien_tuc.lower()
            skip_phrases = [
                "không áp dụng",
                "not applicable",
                "đáp ứng giả định hoạt động liên tục",
                "meets the going concern",
            ]
            return not any(phrase in text for phrase in skip_phrases)
        return False

    def get_section_summary(self) -> Dict[str, bool]:
        return {
            "dac_diem_hoat_dong": self.dac_diem_hoat_dong is not None,
            "ky_ke_toan_tien_te": bool(self.ky_ke_toan_tien_te),
            "chuan_muc_che_do": bool(self.chuan_muc_che_do),
            "chinh_sach_hoat_dong_lien_tuc": bool(self.chinh_sach_hoat_dong_lien_tuc),
            "bo_sung_bang_can_doi": self.bo_sung_bang_can_doi is not None,
            "bo_sung_ket_qua_kd": self.bo_sung_ket_qua_kd is not None,
            "bo_sung_luu_chuyen_tien_te": self.bo_sung_luu_chuyen_tien_te is not None,
            "nhung_thong_tin_khac": self.nhung_thong_tin_khac is not None,
        }

    def get_all_tables(self) -> Dict[str, List[dict]]:
        result = {}
        for sub_model_field in ("bo_sung_bang_can_doi", "bo_sung_ket_qua_kd", "bo_sung_luu_chuyen_tien_te", "nhung_thong_tin_khac"):
            obj = getattr(self, sub_model_field, None)
            if obj is None:
                continue
            if isinstance(obj, BaseModel):
                for field_name, value in obj:
                    if isinstance(value, list) and value:
                        result[field_name] = value
            elif isinstance(obj, dict):
                for key, value in obj.items():
                    if isinstance(value, list) and value:
                        result[key] = value
        return result