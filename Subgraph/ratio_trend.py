import re
import math
from typing import Any, Dict, List, Tuple, Optional
from collections import defaultdict

from Class.FinancialState import FinancialReportState

RATIO_FIELDS = ("ROE", "ROA", "Debt_to_Equity", "Net_Margin")
TREND_FIELDS = ("doanh_thu", "loi_nhuan_sau_thue", "tong_tai_san")
FINANCIAL_LINE_ITEMS_FOR_BENFORD = ("doanh_thu", "loi_nhuan_sau_thue", "tong_tai_san", "von_chu_so_huu", "no_phai_tra")

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

def check_period_anomalies(keys: List[str], dataset: Dict[str, Dict[str, float]], threshold: float = 0.5) -> List[Dict[str, Any]]:
    flags: List[Dict[str, Any]] = []

    # Prepare data for multivariate analysis
    multivariate_data = []
    valid_keys = []

    for key in keys:
        period_data = dataset.get(key, {})
        # Extract values for TREND_FIELDS for multivariate analysis
        values = []
        valid = True
        for field in TREND_FIELDS:
            val = period_data.get(field, 0.0) or 0.0
            if isinstance(val, (int, float)) and not (isinstance(val, float) and math.isnan(val)):
                values.append(float(val))
            else:
                valid = False
                break
        if valid and len(values) == len(TREND_FIELDS):
            multivariate_data.append(values)
            valid_keys.append(key)

    # Statistical Process Control (SPC) for each field - Control Charts
    for field_idx, field in enumerate(TREND_FIELDS):
        values = []
        valid_periods = []
        for i, key in enumerate(keys):
            val = dataset.get(key, {}).get(field, 0.0) or 0.0
            if isinstance(val, (int, float)) and not (isinstance(val, float) and math.isnan(val)):
                values.append(float(val))
                valid_periods.append(key)

        if len(values) >= 4:  # Need sufficient data for control limits
            # Calculate mean and standard deviation
            mean_val = sum(values) / len(values)
            if len(values) > 1:
                variance = sum((x - mean_val) ** 2 for x in values) / (len(values) - 1)
                std_val = math.sqrt(variance) if variance > 0 else 0
            else:
                std_val = 0

            # Control limits (using 3-sigma rules)
            ucl = mean_val + 3 * std_val
            lcl = mean_val - 3 * std_val

            # Check each point against control limits
            for i, (period_key, value) in enumerate(zip(valid_periods, values)):
                if value > ucl or value < lcl:
                    # Calculate how many sigma away from mean
                    sigma_away = abs(value - mean_val) / std_val if std_val > 0 else 0
                    flags.append({
                        "period_key": period_key,
                        "flag_type": "spc_anomaly",
                        "field": field,
                        "message": f"Giá trị {field} ở kỳ {period_key} ({value:,.0f}) ngoài phạm vi điều khiển (LCL={lcl:,.0f}, UCL={ucl:,.0f}), {sigma_away:.1f}σ từ trung bình",
                        "severity": "HIGH" if sigma_away > 4 else "MEDIUM",
                        "value": value,
                        "mean": mean_val,
                        "std": std_val,
                        "lcl": lcl,
                        "ucl": ucl
                    })

    # Multivariate anomaly detection using simple distance-based approach
    if len(multivariate_data) >= 4:
        # Calculate centroid (mean of each dimension)
        centroid = [sum(dim) / len(dim) for dim in zip(*multivariate_data)]

        # Calculate distances from centroid
        distances = []
        for i, point in enumerate(multivariate_data):
            dist = math.sqrt(sum((point[j] - centroid[j]) ** 2 for j in range(len(point))))
            distances.append((valid_keys[i], dist))

        # Calculate statistics for distances
        if len(distances) > 1:
            dist_values = [d[1] for d in distances]
            mean_dist = sum(dist_values) / len(dist_values)
            if len(dist_values) > 1:
                dist_variance = sum((d - mean_dist) ** 2 for d in dist_values) / (len(dist_values) - 1)
                std_dist = math.sqrt(dist_variance) if dist_variance > 0 else 0
            else:
                std_dist = 0

            # Flag points that are too far from centroid (using 2-sigma for multivariate)
            threshold_dist = mean_dist + 2 * std_dist
            for period_key, dist in distances:
                if dist > threshold_dist and std_dist > 0:
                    flags.append({
                        "period_key": period_key,
                        "flag_type": "multivariate_anomaly",
                        "field": "multivariate",
                        "message": f"Kỳ {period_key} có unusual combination of financial metrics (khoảng cách tới trung bình: {dist:.2f}, ngưỡng: {threshold_dist:.2f})",
                        "severity": "MEDIUM",
                        "distance": dist,
                        "mean_distance": mean_dist,
                        "std_distance": std_dist
                    })

    # Benford's Law analysis for certain financial line items
    for field in FINANCIAL_LINE_ITEMS_FOR_BENFORD:
        # Collect first digits from all periods for this field
        first_digits = []
        valid_periods_benford = []

        for key in keys:
            val = dataset.get(key, {}).get(field, 0.0) or 0.0
            # Only consider positive values for Benford's Law
            if isinstance(val, (int, float)) and val > 0:
                # Get first non-zero digit
                val_str = str(abs(val))
                # Remove leading zeros and decimal point
                val_str = val_str.lstrip('0').replace('.', '')
                if val_str and val_str[0].isdigit():
                    first_digit = int(val_str[0])
                    if 1 <= first_digit <= 9:
                        first_digits.append(first_digit)
                        valid_periods_benford.append(key)

        # Check if we have sufficient data for Benford's analysis
        if len(first_digits) >= 10:
            # Count frequency of each first digit
            digit_counts = [0] * 10  # indices 0-9, we'll use 1-9
            for digit in first_digits:
                digit_counts[digit] += 1

            # Expected frequencies according to Benford's Law
            expected_freq = [0] * 10
            for d in range(1, 10):
                expected_freq[d] = math.log10(1 + 1/d) * 100  # as percentage

            # Actual frequencies as percentages
            actual_freq = [(count / len(first_digits)) * 100 for count in digit_counts]

            # Chi-square test for goodness of fit
            chi_square = 0
            for d in range(1, 10):
                expected = expected_freq[d] * len(first_digits) / 100
                actual = digit_counts[d]
                if expected > 0:
                    chi_square += ((actual - expected) ** 2) / expected

            # Critical value for chi-square with 8 degrees of freedom at 0.05 significance level is 15.51
            # If chi-square > critical value, we reject the null hypothesis (data follows Benford's Law)
            if chi_square > 15.51:
                # Find which digits deviate most
                max_deviation = 0
                max_digit = -1
                for d in range(1, 10):
                    deviation = abs(actual_freq[d] - expected_freq[d])
                    if deviation > max_deviation:
                        max_deviation = deviation
                        max_digit = d

                flags.append({
                    "period_key": "multiple",  # This affects multiple periods
                    "flag_type": "benford_anomaly",
                    "field": field,
                    "message": f"Phân phối chữ số đầu tiên của {field} không tuân theo luật Benford (chi-square={chi_square:.2f}), con số {max_digit}สดง sự lệch nhất",
                    "severity": "LOW",  # Benford deviations are often not indicative of fraud in financial statements
                    "chi_square": chi_square,
                    "digit_deviations": {d: actual_freq[d] - expected_freq[d] for d in range(1, 10)}
                })

    # Original percentage change anomaly detection (keeping for backward compatibility)
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

    return flags

def check_forecast_consistency(dataset: Dict[str, Dict[str, float]], 
                              forecasts: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Check consistency between forecasted values and actual values.
    
    Args:
        dataset: Actual financial data by period
        forecasts: Forecast data from financial_forecasting_node
        
    Returns:
        List of validation flags for inconsistencies
    """
    flags: List[Dict[str, Any]] = []
    
    # Check each scope in forecasts
    for scope, forecast_data in forecasts.items():
        if scope not in dataset:
            continue
            
        actual_data = dataset[scope]
        if not isinstance(actual_data, dict):
            continue
            
        # Get the most recent period for comparison
        actual_periods = sorted(actual_data.keys(), key=period_sort_key)
        if not actual_periods:
            continue
            
        most_recent_period = actual_periods[-1]
        actual_period_data = actual_data[most_recent_period]
        
        # Check each metric that has forecasts
        for metric, forecast_info in forecast_data.items():
            if not isinstance(forecast_info, dict) or "point_forecast" not in forecast_info:
                continue
                
            # Get the actual value for this metric in the most recent period
            actual_value = actual_period_data.get(metric)
            if actual_value is None:
                continue
                
            try:
                actual_value = float(actual_value)
                # Forecast for the next period (first in the forecast list)
                forecast_values = forecast_info["point_forecast"]
                if not forecast_values or len(forecast_values) == 0:
                    continue
                    
                forecast_value = float(forecast_values[0])  # First forecasted value
                
                # Calculate percentage difference
                if actual_value != 0:
                    pct_diff = abs((forecast_value - actual_value) / actual_value) * 100
                    # Flag if forecast differs significantly from actual (>20%)
                    if pct_diff > 20.0:
                        flags.append({
                            "period_key": most_recent_period,
                            "flag_type": "forecast_inconsistency",
                            "field": metric,
                            "message": f"Dự báo {metric} ({forecast_value:,.0f}) khác biệt đáng kể với giá trị thực tế ({actual_value:,.0f}), chênh lệch {pct_diff:.1f}%",
                            "severity": "MEDIUM",
                            "forecast_value": forecast_value,
                            "actual_value": actual_value,
                            "percent_difference": pct_diff
                        })
            except (ValueError, TypeError):
                continue
    
    return flags

def ratio_trend_engine(state: FinancialReportState) -> dict:
    metrics = state.get("period_metrics") or {}
    _scope, dataset = select_scope(metrics)

    ratios: Dict[str, Dict[str, float]] = {name: {} for name in RATIO_FIELDS}
    for period_key, data in dataset.items():
        period_ratios = compute_period_ratios(data)
        for name in RATIO_FIELDS:
            ratios[name][period_key] = period_ratios.get(name, 0.0)

    trends = compute_period_trends(dataset)
    keys = sorted(dataset.keys(), key=period_sort_key)
    flags = list(state.get("validation_flags") or [])
    flags.extend(check_period_anomalies(keys, dataset))

    # Also check for consistency between forecasted values and actual values if forecasts exist
    # This would typically be done in a separate validation step, but we can add basic checks here
    forecasts = state.get("financial_forecasts") or {}
    if forecasts:
        # Add forecast consistency checks to flags
        forecast_consistency_flags = check_forecast_consistency(dataset, forecasts)
        flags.extend(forecast_consistency_flags)

    return {"ratios": ratios, "trends": trends, "validation_flags": flags}