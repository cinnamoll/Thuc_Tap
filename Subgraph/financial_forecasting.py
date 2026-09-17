import math
import json
import os
from typing import Any, Dict, List
from Class.FinancialState import FinancialReportState
from Subgraph.ratio_trend import build_period_dataset, period_sort_key, select_scope

DEFAULT_SMOOTHING_ALPHA = 0.3
DEFAULT_FORECAST_STEPS = 1
DEFAULT_CONFIDENCE_LEVEL = 0.95

def simple_exponential_smoothing_forecast(values: List[float], alpha: float = DEFAULT_SMOOTHING_ALPHA, steps_ahead: int = DEFAULT_FORECAST_STEPS) -> List[float]:
    if not values:
        return [0.0] * steps_ahead
    s = values[0]
    for val in values[1:]:
        s = alpha * val + (1.0 - alpha) * s
    return [round(s, 2)] * steps_ahead

def linear_trend_forecast(values: List[float], steps_ahead: int = DEFAULT_FORECAST_STEPS) -> List[float]:
    n = len(values)
    if n == 0:
        return [0.0] * steps_ahead
    if n == 1:
        return [values[0]] * steps_ahead

    x_mean = (n - 1) / 2.0
    y_mean = sum(values) / float(n)

    numerator = sum((i - x_mean) * (values[i] - y_mean) for i in range(n))
    denominator = sum((i - x_mean) ** 2 for i in range(n))

    slope = numerator / denominator if denominator != 0 else 0.0
    intercept = y_mean - slope * x_mean

    forecasts = []
    for step in range(1, steps_ahead + 1):
        target_x = (n - 1) + step
        pred = slope * target_x + intercept
        forecasts.append(round(pred, 2))
    return forecasts

def compound_growth_forecast(values: List[float], steps_ahead: int = DEFAULT_FORECAST_STEPS) -> List[float]:
    n = len(values)
    if n < 2 or values[0] <= 0 or values[-1] <= 0:
        return [values[-1]] * steps_ahead if n > 0 else [0.0] * steps_ahead

    cagr = (values[-1] / values[0]) ** (1.0 / (n - 1)) - 1.0
    forecasts = []
    last_val = values[-1]
    for step in range(1, steps_ahead + 1):
        pred = last_val * ((1.0 + cagr) ** step)
        forecasts.append(round(pred, 2))
    return forecasts

def driver_based_revenue_forecast(historical_revenue: List[float], historical_volume: List[float] = None, historical_price: List[float] = None, steps_ahead: int = DEFAULT_FORECAST_STEPS) -> List[float]:
    if historical_volume and historical_price and len(historical_volume) == len(historical_revenue) and len(historical_price) == len(historical_revenue):
        vol_fc = linear_trend_forecast(historical_volume, steps_ahead)
        price_fc = linear_trend_forecast(historical_price, steps_ahead)
        return [round(v * p, 2) for v, p in zip(vol_fc, price_fc)]
    return linear_trend_forecast(historical_revenue, steps_ahead)

def calculate_prediction_intervals(point_forecast: float, historical_errors: List[float], confidence_level: float = DEFAULT_CONFIDENCE_LEVEL) -> Dict[str, float]:
    if not historical_errors:
        std_err = abs(point_forecast) * 0.1
    else:
        variance = sum(e ** 2 for e in historical_errors) / max(1, len(historical_errors))
        std_err = math.sqrt(variance)

    z = 1.96 if confidence_level >= 0.95 else 1.28
    margin = z * std_err

    return {
        "point_forecast": round(point_forecast, 2),
        "lower_bound": round(point_forecast - margin, 2),
        "upper_bound": round(point_forecast + margin, 2),
        "margin": round(margin, 2),
    }

def financial_forecasting_node(state: FinancialReportState) -> dict:
    metrics = state.get("period_metrics") or {}
    _scope, fallback = select_scope(metrics)
    dataset = build_period_dataset(metrics) or fallback

    keys = sorted(dataset.keys(), key=period_sort_key)
    if len(keys) < 2:
        return {"forecasts": {}, "prediction_intervals": {}}

    target_fields = ["doanh_thu", "loi_nhuan_sau_thue", "tong_tai_san", "von_chu_so_huu"]
    forecasts: Dict[str, Dict[str, Any]] = {}
    intervals: Dict[str, Dict[str, Any]] = {}

    for field in target_fields:
        series = [dataset[k].get(field) or 0.0 for k in keys]
        ses_fc = simple_exponential_smoothing_forecast(series)[0]
        trend_fc = linear_trend_forecast(series)[0]
        cagr_fc = compound_growth_forecast(series)[0]

        # Calculate historical errors for trend forecast
        fitted = linear_trend_forecast(series[:-1], steps_ahead=1) if len(series) > 1 else [series[0]]
        errors = [series[-1] - fitted[0]] if fitted else []

        pred_interval = calculate_prediction_intervals(trend_fc, errors)

        forecasts[field] = {
            "exponential_smoothing": ses_fc,
            "linear_trend": trend_fc,
            "compound_growth": cagr_fc,
            "recommended": trend_fc,
        }
        intervals[field] = pred_interval

    batch_id = state.get("batch_id", "unknown")
    temp_dir = os.path.join("financial_forecast_output", batch_id)
    os.makedirs(temp_dir, exist_ok=True)

    forecasts_file = os.path.join(temp_dir, "forecasts.json")
    with open(forecasts_file, 'w') as f:
        json.dump(forecasts, f, ensure_ascii=False, indent=2)

    intervals_file = os.path.join(temp_dir, "prediction_intervals.json")
    with open(intervals_file, 'w') as f:
        json.dump(intervals, f, ensure_ascii=False, indent=2)

    return {"forecasts_path": forecasts_file, "prediction_intervals_path": intervals_file}