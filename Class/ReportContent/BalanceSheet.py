from pydantic import BaseModel, field_validator, ConfigDict
from typing import Optional, Dict, List, Any

from parse_financial_number import parse_number

class BalanceSheetLine(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    prefix: Optional[str] = None
    chi_tieu: str
    ma_so: Optional[str] = None
    thuyet_minh: Optional[str] = None
    so_cuoi_ky: Optional[float] = None
    so_dau_nam: Optional[float] = None

    @field_validator("so_cuoi_ky", "so_dau_nam", mode="before")
    @classmethod
    def parse_numeric(cls, value):
        return parse_number(value)

class BalanceSheet(BaseModel):
    page_start: int = 0
    page_end: int = 0
    
    year: Optional[int] = None
    scope: Optional[str] = None
    period_key: Optional[str] = None
    sections: Dict[str, List[BalanceSheetLine]] = {}

    tai_san_ngan_han: Optional[float] = None      
    tai_san_dai_han: Optional[float] = None       
    tong_tai_san: Optional[float] = None          
    no_phai_tra: Optional[float] = None           
    von_chu_so_huu: Optional[float] = None
    tong_nguon_von: Optional[float] = None        
    
    raw_data: Optional[Any] = None
    
    @field_validator("tong_tai_san", "no_phai_tra", "von_chu_so_huu", "tai_san_ngan_han", "tai_san_dai_han", "tong_nguon_von", mode="before")
    @classmethod
    def parse_aggregate(cls, value):
        return parse_number(value)

    def check_identity(self) -> Optional[str]:
        if self.tong_tai_san and self.no_phai_tra is not None and self.von_chu_so_huu is not None:
            expected = (self.no_phai_tra or 0) + (self.von_chu_so_huu or 0)
            diff = abs(self.tong_tai_san - expected)
            if diff > 1e-2:
                return (
                    f"Sai lệch bảng cân đối năm {self.year}: "
                    f"Tài sản ({self.tong_tai_san:.2f}) != "
                    f"Nợ PT + Vốn CSH ({expected:.2f}), chênh lệch: {diff:.2f}"
                )
        return None