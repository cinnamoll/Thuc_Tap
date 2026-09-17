from typing import List, Dict, Any

from Subgraph.ratio_trend import period_sort_key

def slice_dataset(dataset: Dict[str, Dict[str, float]], period_key: str) -> Dict[str, Dict[str, float]]:
    data = (dataset or {}).get(period_key)
    return {period_key: data} if data is not None else {}

def slice_ratios(ratios: Dict[str, Dict[str, float]], period_key: str) -> Dict[str, Dict[str, float]]:
    out: Dict[str, Dict[str, float]] = {}
    for name, series in (ratios or {}).items():
        if isinstance(series, dict) and series.get(period_key) is not None:
            out[name] = {period_key: series.get(period_key)}
    return out

def slice_trends(trends: Dict[str, Dict[str, float]], period_key: str) -> Dict[str, Dict[str, float]]:
    out: Dict[str, Dict[str, float]] = {}
    for field, entry in (trends or {}).items():
        kept = {
            key: value for key, value in (entry or {}).items()
            if key == "CAGR_%" or key.endswith(f"_{period_key}_%")
        }
        if kept:
            out[field] = kept
    return out

def slice_flags(flags: List[Dict[str, Any]], period_key: str) -> List[Dict[str, Any]]:
    return [f for f in (flags or []) if not f.get("period_key") or str(f.get("period_key")) == str(period_key)]

def slice_reconciliation(reconciliation: List[Dict[str, Any]], period_key: str) -> List[Dict[str, Any]]:
    return [r for r in (reconciliation or []) if str(r.get("period_key")) == str(period_key)]

def slice_narratives(narrative_store: List[Dict[str, Any]], period_key: str) -> List[Dict[str, Any]]:
    return [n for n in (narrative_store or []) if str(n.get("period_key")) == str(period_key)]

def previous_period_key(dataset: Dict[str, Dict[str, float]], period_key: str) -> str:
    keys = sorted((dataset or {}).keys(), key=period_sort_key)
    if period_key not in keys:
        return ""
    index = keys.index(period_key)
    return keys[index - 1] if index > 0 else ""

def period_deltas(current: Dict[str, float], previous: Dict[str, float], fields: List[str]) -> Dict[str, Dict[str, float]]:
    deltas: Dict[str, Dict[str, float]] = {}
    for field in fields:
        cur = (current or {}).get(field)
        prev = (previous or {}).get(field)
        if cur is None or prev is None:
            continue
        deltas[field] = {
            "ky_nay": round(float(cur), 2),
            "ky_truoc": round(float(prev), 2),
            "thay_doi": round(float(cur) - float(prev), 2),
            "thay_doi_%": round(((cur - prev) / abs(prev)) * 100, 2) if prev else 0.0,
        }
    return deltas

def next_period_key(dataset: Dict[str, Dict[str, float]], period_key: str) -> str:
    keys = sorted((dataset or {}).keys(), key=period_sort_key)
    if period_key not in keys:
        return ""
    index = keys.index(period_key)
    return keys[index + 1] if index < len(keys) - 1 else ""