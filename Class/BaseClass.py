from pydantic import BaseModel
from typing import Optional, Literal

class BaseAction(BaseModel):
    file_path: str
    file_format: str
    output_path: str
    reason: str

    rows_affected: Optional[int] = None
    rows_affected_pct: Optional[float] = None
    risk_level: Optional[Literal["low", "medium", "high"]] = None