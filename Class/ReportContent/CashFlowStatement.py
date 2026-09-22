from pydantic import BaseModel, field_validator, ConfigDict
from typing import Optional, Dict, List, Any

from Class.parse_financial_number import parse_number

class CashFlowLine(BaseModel):
    model_config = ConfigDict(validate_assignment=True)
    prefix: Optional[str] = None
    chi_tieu: str
    ma_so: Optional[str] = None
    thuyet_minh: Optional[str]= None
    luy_ke_ky_nay: Optional[float] = None
    luy_ke_ky_truoc: Optional[float] = None

    @field_validator("luy_ke_ky_nay", "luy_ke_ky_truoc", mode="before")
    @classmethod
    def parse_numeric(cls, value):
        return parse_number(value)

class CashFlowStatement(BaseModel):
    model_config = ConfigDict(validate_assignment=True)
    page_start: int = 0
    page_end: int = 0
    
    year: Optional[int] = None
    scope: Optional[str] = None
    period_key: Optional[str] = None
    sections: Dict[str, List[CashFlowLine]] = {}

    luu_chuyen_kinh_doanh: Optional[float] = None    
    luu_chuyen_dau_tu: Optional[float] = None        
    luu_chuyen_tai_chinh: Optional[float] = None     

    luu_chuyen_trong_ky: Optional[float] = None      
    tien_dau_ky: Optional[float] = None                    
    tien_cuoi_ky: Optional[float] = None                   

    raw_data: Optional[Any] = None

    @field_validator(
        "luu_chuyen_kinh_doanh", "luu_chuyen_dau_tu", "luu_chuyen_tai_chinh", "luu_chuyen_trong_ky", "tien_dau_ky", "tien_cuoi_ky", 
        mode="before"
    )
    @classmethod
    def parse_aggregate(cls, value):
        return parse_number(value)

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