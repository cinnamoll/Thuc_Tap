from pydantic import BaseModel
from typing import Optional

class EDAInsight(BaseModel):
    file_path: str
    file_format: str
    column: str
    metric_name: str
    value: float
    n_rows: int
    chart_path: Optional[str] = None