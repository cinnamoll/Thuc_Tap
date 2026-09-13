from pydantic import BaseModel, field_validator, ConfigDict
from typing import Optional, Dict, List, Any

from parse_financial_number import parse_number

class IncomeStatementLine(BaseModel):
    model_config = ConfigDict(validate_assignment=True)
    stt: Optional[str] = None
    chi_tieu: str
    ma_so: Optional[str] = None
    thuyet_minh: Optional[str] = None
    ky_nay: Optional[float] = None
    ky_truoc: Optional[float] = None
    luy_ke_ky_nay: Optional[float] = None
    luy_ke_ky_truoc: Optional[float] = None

    @field_validator("ky_nay", "ky_truoc", "luy_ke_ky_nay", "luy_ke_ky_truoc", mode="before")
    @classmethod
    def parse_numeric(cls, value):
        return parse_number(value)

class IncomeStatement(BaseModel):
    model_config = ConfigDict(validate_assignment=True)
    page_start: int = 0
    page_end: int = 0
    
    year: Optional[int] = None
    scope: Optional[str] = None
    period_key: Optional[str] = None
    line_items: List[IncomeStatementLine] = []

    doanh_thu: Optional[float] = None               
    cac_khoan_giam_tru: Optional[float] = None       
    doanh_thu_thuan: Optional[float] = None          
    gia_von_hang_ban: Optional[float] = None         
    loi_nhuan_gop: Optional[float] = None            
    doanh_thu_tai_chinh: Optional[float] = None      
    chi_phi_tai_chinh: Optional[float] = None        
    chi_phi_ban_hang: Optional[float] = None         
    chi_phi_quan_ly: Optional[float] = None          
    loi_nhuan_thuan_kd: Optional[float] = None       
    loi_nhuan_truoc_thue: Optional[float] = None     
    chi_phi_thue_tndn: Optional[float] = None        
    loi_nhuan_sau_thue: Optional[float] = None       

    raw_data: Optional[Any] = None

    @field_validator("doanh_thu", "cac_khoan_giam_tru", "doanh_thu_thuan","gia_von_hang_ban", "loi_nhuan_gop", "doanh_thu_tai_chinh",
                     "chi_phi_tai_chinh", "chi_phi_ban_hang", "chi_phi_quan_ly", "loi_nhuan_thuan_kd", "loi_nhuan_truoc_thue",
                     "chi_phi_thue_tndn", "loi_nhuan_sau_thue", mode="before")
    @classmethod
    def parse_aggregate(cls, value):
        return parse_number(value)

    def compute_net_margin(self) -> Optional[float]:
        if self.doanh_thu and self.doanh_thu != 0 and self.loi_nhuan_sau_thue is not None:
            return round((self.loi_nhuan_sau_thue / self.doanh_thu) * 100, 2)
        return None

    def compute_gross_margin(self) -> Optional[float]:
        dt = self.doanh_thu_thuan or self.doanh_thu
        if dt and dt != 0 and self.loi_nhuan_gop is not None:
            return round((self.loi_nhuan_gop / dt) * 100, 2)
        return None
