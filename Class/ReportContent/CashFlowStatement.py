from pydantic import BaseModel, field_validator
from typing import Optional, Dict, List, Any

class CashFlowLine(BaseModel):
    prefix: Optional[str] = None
    chi_tieu: str
    ma_so: Optional[str] = None
    thuyet_minh: Optional[str]= None
    luy_ke_ky_nay: Optional[float] = None
    luy_ke_ky_truoc: Optional[float] = None

    @field_validator("luy_ke_ky_nay", "luy_ke_ky_truoc", mode="before")
    @classmethod
    def parse_numeric(cls, value):
        if value is None or value == "" or value == "-":
            return None
        if isinstance(value, (int, float)):
            return float(value)
        s = str(value).strip()
        negative = s.startswith("(") and s.endswith(")")
        if negative:
            s = s[1:-1]
        s = s.replace(" ", "")
        if s.count(".") > 1 and "," not in s:
            s = s.replace(".", "")
        elif "," in s:
            s = s.replace(",", "")
        try:
            number = float(s)
            return -number if negative else number
        except ValueError:
            return None

class CashFlowStatement(BaseModel):
    page_start: int = 0
    page_end: int = 0
    
    year: Optional[int] = None
    sections: Dict[str, List[CashFlowLine]] = {}

    luu_chuyen_kinh_doanh: Optional[float] = None    
    luu_chuyen_dau_tu: Optional[float] = None        
    luu_chuyen_tai_chinh: Optional[float] = None     

    luu_chuyen_trong_ky: Optional[float] = None      
    tien_dau_ky: Optional[float] = None                    
    tien_cuoi_ky: Optional[float] = None                   

    raw_data: Optional[Dict[str, Any]] = None

    @field_validator(
        "luu_chuyen_kinh_doanh", "luu_chuyen_dau_tu", "luu_chuyen_tai_chinh", "luu_chuyen_trong_ky", "tien_dau_ky", "tien_cuoi_ky", 
        mode="before"
    )
    @classmethod
    def parse_aggregate(cls, value):
        if value is None or value == "" or value == "-":
            return None
        if isinstance(value, (int, float)):
            return float(value)
        s = str(value).strip().replace(" ", "").replace(",", "")
        if s.count(".") > 1:
            s = s.replace(".", "")
        try:
            return float(s)
        except ValueError:
            return None

    def check_cash_reconciliation(self) -> Optional[str]:
        if (self.tien_cuoi_ky is not None and self.tien_dau_ky is not None and self.luu_chuyen_trong_ky is not None):
            expected = self.tien_dau_ky + self.luu_chuyen_trong_ky
            diff = abs(self.tien_cuoi_ky - expected)
            if diff > 1e-2:
                return (
                    f"Sai lệch cân đối tiền năm {self.year}: "
                    f"Tiền cuối kỳ ({self.tien_cuoi_ky:.2f}) != "
                    f"Tiền đầu kỳ + LC thuần ({expected:.2f}), chênh lệch: {diff:.2f}"
                )
        return None

    def check_net_flow_consistency(self) -> Optional[str]:
        if (self.luu_chuyen_trong_ky is not None and self.luu_chuyen_kinh_doanh is not None and 
            self.luu_chuyen_dau_tu is not None and self.luu_chuyen_tai_chinh is not None):
            expected = (self.luu_chuyen_kinh_doanh + self.luu_chuyen_dau_tu + self.luu_chuyen_tai_chinh)
            diff = abs(self.luu_chuyen_trong_ky - expected)
            if diff > 1e-2:
                return (
                    f"Sai lệch lưu chuyển thuần năm {self.year}: "
                    f"Tổng ({self.luu_chuyen_trong_ky:.2f}) != "
                    f"KD + ĐT + TC ({expected:.2f}), chênh lệch: {diff:.2f}"
                )
        return None