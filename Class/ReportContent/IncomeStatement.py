from pydantic import BaseModel, field_validator
from typing import Optional, Dict, List, Any

class IncomeStatementLine(BaseModel):
    stt: Optional[str] = None
    chi_tieu: str
    ma_so: Optional[str] = None
    thuyet_minh: Optional[str] = None
    ky_nay: Optional[float] = None
    ky_truoc: Optional[float] = None
    luy_ke_ky_nay: Optional[float] = None
    luy_ke_ky_truoc: Optional[float] = None

    @field_validator("ky_nay", "ky_truoc", mode="before")
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

class IncomeStatement(BaseModel):
    page_start: int = 0
    page_end: int = 0
    
    year: Optional[int] = None
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

    raw_data: Optional[List[Dict[str, Any]]] = None

    @field_validator("doanh_thu", "cac_khoan_giam_tru", "doanh_thu_thuan",
                     "gia_von_hang_ban", "loi_nhuan_gop", "doanh_thu_tai_chinh",
                     "chi_phi_tai_chinh", "chi_phi_ban_hang", "chi_phi_quan_ly",
                     "loi_nhuan_thuan_kd", "loi_nhuan_truoc_thue",
                     "chi_phi_thue_tndn", "loi_nhuan_sau_thue", mode="before")
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

    def compute_net_margin(self) -> Optional[float]:
        if self.doanh_thu and self.doanh_thu != 0 and self.loi_nhuan_sau_thue is not None:
            return round((self.loi_nhuan_sau_thue / self.doanh_thu) * 100, 2)
        return None

    def compute_gross_margin(self) -> Optional[float]:
        dt = self.doanh_thu_thuan or self.doanh_thu
        if dt and dt != 0 and self.loi_nhuan_gop is not None:
            return round((self.loi_nhuan_gop / dt) * 100, 2)
        return None
