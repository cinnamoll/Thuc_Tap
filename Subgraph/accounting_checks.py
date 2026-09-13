from typing import Any, Dict, List
import pandas as pd

from Class.FinancialState import FinancialReportState
from Subgraph.eda import compute_consistency_flags
from Subgraph.validator import compute_identity_flags

def dedupe_flags(flags: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out = []
    for f in flags:
        key = (f.get("period_key"), f.get("scope"), f.get("flag_type"), f.get("field"), f.get("message"))
        if key in seen:
            continue
        seen.add(key)
        out.append(f)
    return out

def run_accounting_checks(state: FinancialReportState) -> dict:
    rows = list(state.get("harmonized_dataset") or [])
    if not rows:
        return {"validation": True, "validation_error": None, "validation_flags": []}

    df = pd.DataFrame(rows)
    flags: List[Dict[str, Any]] = []
    flags.extend(compute_consistency_flags(df))
    flags.extend(compute_identity_flags(df))

    return {"validation": True, "validation_error": None, "validation_flags": dedupe_flags(flags)}