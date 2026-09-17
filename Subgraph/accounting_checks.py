from typing import Any, Dict, List
import pandas as pd

from Class.FinancialState import FinancialReportState

def compute_identity_flags(df: pd.DataFrame) -> List[Dict[str, Any]]:
    flags: List[Dict[str, Any]] = []
    if df.empty or "line_item_canonical" not in df.columns or "value" not in df.columns:
        return flags

    group_cols = [c for c in ["period_key", "scope"] if c in df.columns]
    if not group_cols:
        return flags

    for keys, group in df.groupby(group_cols):
        period_key = keys[0] if isinstance(keys, tuple) else keys
        scope = keys[1] if isinstance(keys, tuple) and len(keys) > 1 else "unknown"

        metrics = dict(zip(group["line_item_canonical"], group["value"]))
        assets = float(metrics.get("tong_tai_san") or 0.0)
        liabilities = float(metrics.get("no_phai_tra") or 0.0)
        equity = float(metrics.get("von_chu_so_huu") or 0.0)

        if assets and (liabilities or equity):
            diff = abs(assets - (liabilities + equity))
            if diff > 1.0:
                flags.append({
                    "period_key": str(period_key),
                    "scope": str(scope),
                    "flag_type": "identity_violation",
                    "field": "tong_tai_san",
                    "message": f"BCĐKT không cân bằng: Tài sản ({assets:,.0f}) != Nợ ({liabilities:,.0f}) + Vốn ({equity:,.0f}), lệch {diff:,.0f}",
                    "severity": "HIGH",
                })
    return flags

def compute_consistency_flags(df: pd.DataFrame) -> List[Dict[str, Any]]:
    flags: List[Dict[str, Any]] = []
    if df.empty or "value" not in df.columns:
        return flags

    for _, row in df.iterrows():
        val = row.get("value")
        canon = row.get("line_item_canonical")
        if canon in ("tong_tai_san", "doanh_thu") and val is not None and float(val) < 0:
            flags.append({
                "period_key": str(row.get("period_key") or ""),
                "scope": str(row.get("scope") or ""),
                "flag_type": "negative_value_anomaly",
                "field": str(canon),
                "message": f"Giá trị âm bất thường tại chỉ tiêu {canon}: {float(val):,.0f}",
                "severity": "MEDIUM",
            })
    return flags

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

def accounting_check_node(state: FinancialReportState) -> dict:
    rows = list(state.get("harmonized_dataset") or [])
    if not rows:
        return {"validation": True, "validation_error": None, "validation_flags": []}

    df = pd.DataFrame(rows)
    flags: List[Dict[str, Any]] = []
    flags.extend(compute_identity_flags(df))
    flags.extend(compute_consistency_flags(df))

    return {"validation": True, "validation_error": None, "validation_flags": dedupe_flags(flags)}