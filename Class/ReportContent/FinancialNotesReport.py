from pydantic import BaseModel, field_validator
from typing import Optional, Dict, List, Any, Union

class FinancialNotesReport(BaseModel):
    page_start: int = 0
    page_end: int = 0

    year: Optional[int] = None

    dac_diem_hoat_dong: Optional[Dict[str, Any]] = None
    ky_ke_toan_tien_te: Optional[str] = None
    chuan_muc_che_do: Optional[str] = None
    chinh_sach_hoat_dong_lien_tuc: Optional[str] = None
    chinh_sach_khong_lien_tuc: Optional[str] = None

    bo_sung_bang_can_doi: Optional[Dict[str, Any]] = None
    bo_sung_ket_qua_kd: Optional[Union[str, Dict[str, Any]]] = None
    bo_sung_luu_chuyen_tien_te: Optional[Union[str, Dict[str, Any]]] = None
    nhung_thong_tin_khac: Optional[Dict[str, Any]] = None

    tables: Optional[Dict[str, List[dict]]] = None
    raw_data: Optional[Any] = None
    model_config = {"arbitrary_types_allowed": True}

    @field_validator("dac_diem_hoat_dong", "bo_sung_bang_can_doi", "nhung_thong_tin_khac", mode="before")
    @classmethod
    def ensure_dict(cls, value):
        if isinstance(value, str):
            return {"noi_dung": value}
        return value

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
            "bo_sung_ket_qua_kd": bool(self.bo_sung_ket_qua_kd),
            "bo_sung_luu_chuyen_tien_te": bool(self.bo_sung_luu_chuyen_tien_te),
            "nhung_thong_tin_khac": self.nhung_thong_tin_khac is not None,
            "tables": bool(self.tables),
        }