from pydantic import BaseModel
from typing import Optional, Dict, Annotated, List

class EDAInsight(BaseModel):
    column: str
    metric_value: Annotated[Dict[str, float], "str is the metric name, float is its value"]
    chart_paths: Optional[List[str]] = None 