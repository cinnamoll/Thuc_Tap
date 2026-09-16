import math
import re
import json
import os
import uuid
from typing import Any, Dict, List, Tuple

from Class.FinancialState import FinancialReportState

RATIO_FIELDS = ("ROE", "ROA", "Debt_to_Equity", "Net_Margin")
TREND_FIELDS = ("doanh_thu", "loi_nhuan_sau_thue", "tong_tai_san")
BENFORD_EXPECTED_DISTRIBUTION = [0.301, 0.176, 0.125, 0.097, 0.079, 0.067, 0.058, 0.051, 0.046]

def period_sort_key(period_key: Any) -> Tuple[int, int]:
    text = str(period_key or "")
    m = re.match(r"\s*(\d{4})\s*[Qq](\d{1,2})", text)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.search(r"(\d{4})", text)
    return (int(m.group(1)) if m else 0), 0

def select_scope(period_metrics: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    if not period_metrics:
        return "consolidated", {}
    if "consolidated" in period_metrics and period_metrics["consolidated"]:
        return "consolidated", period_metrics["consolidated"]
    scope = sorted(period_metrics.keys())[0]
    return scope, period_metrics.get(scope) or {}

def select_period_data(period_metrics: Dict[str, Any], period_key: str) -> Tuple[str, Dict[str, Any]]:
    ordered_scopes = ["consolidated"] + [s for s in sorted(period_metrics or {}) if s != "consolidated"]
    for scope in ordered_scopes:
        data = ((period_metrics or {}).get(scope) or {}).get(period_key)
        if data:
            return scope, data
    return "", {}

def build_period_dataset(period_metrics: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    periods = set()
    for periods_of_scope in (period_metrics or {}).values():
        periods.update((periods_of_scope or {}).keys())
    return {key: select_period_data(period_metrics, key)[1] for key in periods}

def compute_period_ratios(data: Dict[str, float]) -> Dict[str, float]:
    pat = data.get("loi_nhuan_sau_thue") or 0.0
    equity = data.get("von_chu_so_huu") or 0.0
    assets = data.get("tong_tai_san") or 0.0
    revenue = data.get("doanh_thu") or 0.0
    liabilities = data.get("no_phai_tra") or 0.0
    return {
        "ROE": round((pat / equity) * 100, 2) if equity else 0.0,
        "ROA": round((pat / assets) * 100, 2) if assets else 0.0,
        "Debt_to_Equity": round(liabilities / equity, 2) if equity else 0.0,
        "Net_Margin": round((pat / revenue) * 100, 2) if revenue else 0.0,
    }

def compute_period_trends(dataset: Dict[str, Dict[str, float]]) -> Dict[str, Dict[str, float]]:
    trends: Dict[str, Dict[str, float]] = {}
    keys = sorted(dataset.keys(), key=period_sort_key)
    if len(keys) <= 1:
        return trends

    for field in TREND_FIELDS:
        entry: Dict[str, float] = {}
        for i in range(1, len(keys)):
            prev_key, cur_key = keys[i - 1], keys[i]
            v_prev = dataset.get(prev_key, {}).get(field) or 0.0
            v_cur = dataset.get(cur_key, {}).get(field) or 0.0
            entry[f"QoQ_{cur_key}_%"] = round(((v_cur - v_prev) / abs(v_prev)) * 100, 2) if v_prev else 0.0

            year, quarter = period_sort_key(cur_key)
            same_quarter_last_year = f"{year - 1}Q{quarter}"
            if same_quarter_last_year in dataset:
                v_yoy = dataset[same_quarter_last_year].get(field) or 0.0
                entry[f"YoY_{cur_key}_%"] = round(((v_cur - v_yoy) / abs(v_yoy)) * 100, 2) if v_yoy else 0.0

        start_val = dataset.get(keys[0], {}).get(field) or 0.0
        end_val = dataset.get(keys[-1], {}).get(field) or 0.0
        y0, q0 = period_sort_key(keys[0])
        y1, q1 = period_sort_key(keys[-1])
        n_quarters = (y1 - y0) * 4 + (q1 - q0)
        if start_val > 0 and end_val > 0 and n_quarters > 0:
            years = n_quarters / 4.0
            entry["CAGR_%"] = round((((end_val / start_val) ** (1 / years)) - 1) * 100, 2)
        else:
            entry["CAGR_%"] = 0.0
        trends[field] = entry
    return trends

def calculate_statistical_control_bounds(values: List[float], n_std: float = 2.0) -> Tuple[float, float, float]:
    if not values:
        return 0.0, 0.0, 0.0
    mean_val = sum(values) / len(values)
    variance = sum((v - mean_val) ** 2 for v in values) / max(1, len(values))
    std_dev = math.sqrt(variance)
    return mean_val, mean_val + n_std * std_dev, mean_val - n_std * std_dev

def check_benford_law_anomalies(dataset: Dict[str, Dict[str, float]]) -> List[Dict[str, Any]]:
    flags: List[Dict[str, Any]] = []
    first_digits = []
    for period_data in dataset.values():
        for val in period_data.values():
            if val and abs(val) >= 1.0:
                s = f"{abs(val):.6e}".lstrip("0.")
                first_digit = int(s[0])
                if 1 <= first_digit <= 9:
                    first_digits.append(first_digit)

    if len(first_digits) < 20:
        return flags

    counts = [first_digits.count(d) for d in range(1, 10)]
    total = len(first_digits)
    observed_freq = [c / total for c in counts]

    chi_sq = sum(((obs - exp) ** 2) / exp for obs, exp in zip(observed_freq, BENFORD_EXPECTED_DISTRIBUTION))
    if chi_sq > 0.15:
        flags.append({
            "flag_type": "benford_law_anomaly",
            "field": "all_financial_items",
            "message": f"Phân bố chữ số đầu tiên sai lệch so với luật Benford (Chi-sq diff: {chi_sq:.3f})",
            "severity": "LOW",
        })
    return flags

def check_period_anomalies(keys: List[str], dataset: Dict[str, Dict[str, float]], threshold: float = 0.5) -> List[Dict[str, Any]]:
    flags: List[Dict[str, Any]] = []
    for i in range(1, len(keys)):
        prev_key, cur_key = keys[i - 1], keys[i]
        for field in TREND_FIELDS:
            v_prev = dataset.get(prev_key, {}).get(field) or 0.0
            v_cur = dataset.get(cur_key, {}).get(field) or 0.0
            if not v_prev:
                continue
            change = (v_cur - v_prev) / abs(v_prev)
            if abs(change) > threshold:
                flags.append({
                    "period_key": cur_key,
                    "flag_type": "yoy_anomaly",
                    "field": field,
                    "message": f"Biến động quý {cur_key} của {field}: {change * 100:+.1f}%",
                    "severity": "MEDIUM",
                })

    for field in TREND_FIELDS:
        series = [dataset[k].get(field) or 0.0 for k in keys if dataset[k].get(field) is not None]
        if len(series) >= 3:
            mean_v, ucl, lcl = calculate_statistical_control_bounds(series)
            for k in keys:
                v = dataset[k].get(field) or 0.0
                if v > ucl or v < lcl:
                    flags.append({
                        "period_key": k,
                        "flag_type": "statistical_control_outlier",
                        "field": field,
                        "message": f"Giá trị {field} ({v:,.0f}) nằm ngoài khoảng kiểm soát thống kê 2-sigma [{lcl:,.0f}, {ucl:,.0f}]",
                        "severity": "MEDIUM",
                    })

    flags.extend(check_benford_law_anomalies(dataset))
    return flags

def ratio_trend_engine(state: FinancialReportState) -> dict:
    metrics = state.get("period_metrics") or {}
    _scope, fallback = select_scope(metrics)
    dataset = build_period_dataset(metrics) or fallback

    ratios: Dict[str, Dict[str, float]] = {name: {} for name in RATIO_FIELDS}
    for period_key, data in dataset.items():
        period_ratios = compute_period_ratios(data)
        for name in RATIO_FIELDS:
            ratios[name][period_key] = period_ratios.get(name, 0.0)

    trends = compute_period_trends(dataset)
    keys = sorted(dataset.keys(), key=period_sort_key)
    flags = list(state.get("validation_flags") or [])
    flags.extend(check_period_anomalies(keys, dataset))

    # Create temporary directory for ratio trend data
    batch_id = state.get("batch_id", "unknown")
    temp_dir = os.path.join("temp_data", batch_id)
    os.makedirs(temp_dir, exist_ok=True)

    # Write ratios to temporary file
    ratios_file = os.path.join(temp_dir, "ratios.json")
    with open(ratios_file, 'w') as f:
        json.dump(ratios, f, ensure_ascii=False, indent=2)

    # Write trends to temporary file
    trends_file = os.path.join(temp_dir, "trends.json")
    with open(trends_file, 'w') as f:
        json.dump(trends, f, ensure_ascii=False, indent=2)

    # Write flags to temporary file
    flags_file = os.path.join(temp_dir, "validation_flags.json")
    with open(flags_file, 'w') as f:
        json.dump(flags, f, ensure_ascii=False, indent=2)

    return {
        "ratios_path": ratios_file,
        "trends_path": trends_file,
        "validation_flags_path": flags_file
    }