from pydantic import BaseModel
from typing import Optional, Dict, Annotated, List

def dedupe_list(left: Optional[List[str]], right: Optional[List[str]]) -> List[str]:
    if left is None:
        return list(right or [])
    if right is None:
        return list(left)
    seen = set()
    result = []
    for item in list(left) + list(right):
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result

class EDAInsight(BaseModel):
    column: str
    line_item_canonical: Optional[str] = None
    metric_value: Annotated[Dict[str, float], "str is the metric name, float is its value"]
    chart_paths: Annotated[List[str], dedupe_list] 