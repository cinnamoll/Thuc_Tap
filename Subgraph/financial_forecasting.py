"""
Financial forecasting subgraph for predictive modeling of financial metrics.
"""
from typing import Dict, List, Any, Optional, Tuple
import math
from datetime import datetime, timedelta

from Class.FinancialState import FinancialReportState

DEFAULT_SMOOTHING_ALPHA = 0.3
DEFAULT_FORECAST_STEPS = 4
DEFAULT_CONFIDENCE_LEVEL = 0.8


def simple_exponential_smoothing_forecast(values: List[float], alpha: float = DEFAULT_SMOOTHING_ALPHA, steps_ahead: int = DEFAULT_FORECAST_STEPS) -> List[float]:
    """
    Simple exponential smoothing forecast for time series data.

    Args:
        values: Historical values (most recent last)
        alpha: Smoothing parameter (0 < alpha <= 1)
        steps_ahead: Number of periods to forecast ahead

    Returns:
        List of forecasted values
    """
    if not values:
        return [0.0] * steps_ahead

    # Initialize with first value
    smoothed = values[0]

    # Apply exponential smoothing
    for value in values[1:]:
        smoothed = alpha * value + (1 - alpha) * smoothed

    # Forecast future values (constant forecast based on last smoothed value)
    return [smoothed] * steps_ahead


def linear_trend_forecast(values: List[float], steps_ahead: int = 4) -> List[float]:
    """
    Linear trend forecast using least squares regression.

    Args:
        values: Historical values (most recent last)
        steps_ahead: Number of periods to forecast ahead

    Returns:
        List of forecasted values
    """
    if len(values) < 2:
        return [values[-1] if values else 0.0] * steps_ahead

    n = len(values)
    # x values: 0, 1, 2, ..., n-1
    x_values = list(range(n))
    y_values = values

    # Calculate slope and intercept
    sum_x = sum(x_values)
    sum_y = sum(y_values)
    sum_xy = sum(x * y for x, y in zip(x_values, y_values))
    sum_x2 = sum(x * x for x in x_values)

    slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x) if (n * sum_x2 - sum_x * sum_x) != 0 else 0
    intercept = (sum_y - slope * sum_x) / n

    # Forecast future values
    forecasts = []
    for i in range(steps_ahead):
        x_future = n + i
        y_forecast = slope * x_future + intercept
        forecasts.append(max(0, y_forecast))  # Ensure non-negative for financial values

    return forecasts


def compound_growth_forecast(values: List[float], steps_ahead: int = 4) -> List[float]:
    """
    Compound growth forecast based on historical average growth rate.

    Args:
        values: Historical values (most recent last)
        steps_ahead: Number of periods to forecast ahead

    Returns:
        List of forecasted values
    """
    if len(values) < 2:
        return [values[-1] if values else 0.0] * steps_ahead

    # Calculate period-over-period growth rates
    growth_rates = []
    for i in range(1, len(values)):
        if values[i-1] != 0:
            growth_rate = (values[i] - values[i-1]) / abs(values[i-1])
            growth_rates.append(growth_rate)

    if not growth_rates:
        return [values[-1]] * steps_ahead

    # Average growth rate
    avg_growth_rate = sum(growth_rates) / len(growth_rates)

    # Forecast using compound growth
    last_value = values[-1]
    forecasts = []
    for i in range(steps_ahead):
        forecast_value = last_value * ((1 + avg_growth_rate) ** (i + 1))
        forecasts.append(max(0, forecast_value))

    return forecasts


def driver_based_revenue_forecast(historical_revenue: List[float],
                                 historical_volume: Optional[List[float]] = None,
                                 historical_price: Optional[List[float]] = None,
                                 steps_ahead: int = 4) -> Dict[str, Any]:
    """
    Driver-based revenue forecast: Revenue = Volume × Price.

    Args:
        historical_revenue: Historical revenue values
        historical_volume: Historical volume values (if available)
        historical_price: Historical price values (if available)
        steps_ahead: Number of periods to forecast ahead

    Returns:
        Dictionary with forecast components and combined revenue forecast
    """
    # If we don't have volume/price data, fall back to direct revenue forecasting
    if not historical_volume or not historical_price:
        revenue_forecast = linear_trend_forecast(historical_revenue, steps_ahead)
        return {
            "revenue_forecast": revenue_forecast,
            "volume_forecast": [None] * steps_ahead,
            "price_forecast": [None] * steps_ahead,
            "method": "direct_revenue_trend"
        }

    # Forecast volume and price separately
    volume_forecast = linear_trend_forecast(historical_volume, steps_ahead)
    price_forecast = linear_trend_forecast(historical_price, steps_ahead)

    # Calculate revenue forecast as volume × price
    revenue_forecast = [max(0, v * p) for v, p in zip(volume_forecast, price_forecast)]

    return {
        "revenue_forecast": revenue_forecast,
        "volume_forecast": volume_forecast,
        "price_forecast": price_forecast,
        "method": "driver_based"
    }


def calculate_prediction_intervals(point_forecast: List[float],
                                 historical_errors: List[float],
                                 confidence_level: float = 0.8) -> Tuple[List[float], List[float]]:
    """
    Calculate prediction intervals for forecasts.

    Args:
        point_forecast: Point forecast values
        historical_errors: Historical forecast errors (residuals)
        confidence_level: Confidence level for intervals (e.g., 0.8 for 80%)

    Returns:
        Tuple of (lower_bounds, upper_bounds)
    """
    if not historical_errors:
        # If no error history, use a simple percentage-based interval
        margin = [abs(val) * 0.1 for val in point_forecast]  # 10% margin
        lower_bounds = [max(0, pf - m) for pf, m in zip(point_forecast, margin)]
        upper_bounds = [pf + m for pf, m in zip(point_forecast, margin)]
        return lower_bounds, upper_bounds

    # Calculate standard deviation of historical errors
    mean_error = sum(historical_errors) / len(historical_errors)
    variance = sum((e - mean_error) ** 2 for e in historical_errors) / len(historical_errors)
    std_error = math.sqrt(variance) if variance > 0 else 0

    # For simplicity, using normal distribution critical values
    # 80% confidence: ~1.28 sigma, 95% confidence: ~1.96 sigma
    if confidence_level == 0.8:
        z_score = 1.28
    elif confidence_level == 0.95:
        z_score = 1.96
    else:
        z_score = 1.28  # Default to 80%

    margin = [z_score * std_error] * len(point_forecast)
    lower_bounds = [max(0, pf - m) for pf, m in zip(point_forecast, margin)]
    upper_bounds = [pf + m for pf, m in zip(point_forecast, margin)]

    return lower_bounds, upper_bounds


def financial_forecasting_node(state: FinancialReportState) -> Dict[str, Any]:
    """
    Main financial forecasting node that generates forecasts for key metrics.

    Args:
        state: Current financial report state

    Returns:
        Updated state with forecasts and prediction intervals
    """
    # Get the harmonized period metrics
    period_metrics = state.get("period_metrics") or {}
    forecasts = {}
    prediction_intervals = {}

    # Key metrics to forecast
    metrics_to_forecast = [
        "doanh_thu",           # Revenue
        "loi_nhuan_sau_thue",  # Net Income
        "tong_tai_san",        # Total Assets
        "luu_chuyen_kinh_doanh" # Operating Cash Flow
    ]

    # Process each scope (consolidated, separate, etc.)
    for scope, periods in period_metrics.items():
        if not isinstance(periods, dict):
            continue

        # Sort periods chronologically
        sorted_periods = dict(sorted(periods.items()))
        period_keys = list(sorted_periods.keys())

        # We need at least 2 periods to forecast
        if len(period_keys) < 2:
            continue

        # Initialize forecast storage for this scope
        if scope not in forecasts:
            forecasts[scope] = {}
            prediction_intervals[scope] = {}

        # Forecast each metric
        for metric in metrics_to_forecast:
            # Extract historical values for this metric
            historical_values = []
            for period_key in period_keys:
                period_data = sorted_periods[period_key]
                if isinstance(period_data, dict):
                    value = period_data.get(metric)
                    if value is not None:
                        try:
                            historical_values.append(float(value))
                        except (ValueError, TypeError):
                            pass

            # Need at least 2 values to forecast
            if len(historical_values) >= 2:
                # Generate point forecast using linear trend (simple and interpretable)
                point_forecast = linear_trend_forecast(historical_values, steps_ahead=4)

                # For demonstration, we'll use simple error estimation
                # In practice, we'd use cross-validation or holdout samples
                if len(historical_values) >= 3:
                    # Calculate historical errors using one-step-ahead forecasts
                    errors = []
                    for i in range(2, len(historical_values)):
                        # Forecast using data up to i-1
                        train_values = historical_values[:i]
                        one_step_forecast = linear_trend_forecast(train_values, steps_ahead=1)[0]
                        actual = historical_values[i]
                        errors.append(actual - one_step_forecast)
                else:
                    errors = []

                # Calculate prediction intervals
                lower_80, upper_80 = calculate_prediction_intervals(point_forecast, errors, confidence_level=0.8)
                lower_95, upper_95 = calculate_prediction_intervals(point_forecast, errors, confidence_level=0.95)

                # Store forecasts
                forecasts[scope][metric] = {
                    "point_forecast": point_forecast,
                    "lower_80": lower_80,
                    "upper_80": upper_80,
                    "lower_95": lower_95,
                    "upper_95": upper_95,
                    "historical_values": historical_values,
                    "method": "linear_trend"
                }

    return {
        "financial_forecasts": forecasts,
        "forecast_generated": True
    }


# For testing purposes
if __name__ == "__main__":
    # Test data
    test_state = {
        "period_metrics": {
            "consolidated": {
                "2023Q1": {"doanh_thu": 100000000, "loi_nhuan_sau_thue": 10000000, "tong_tai_san": 500000000},
                "2023Q2": {"doanh_thu": 110000000, "loi_nhuan_sau_thue": 11000000, "tong_tai_san": 520000000},
                "2023Q3": {"doanh_thu": 120000000, "loi_nhuan_sau_thue": 12000000, "tong_tai_san": 540000000},
                "2023Q4": {"doanh_thu": 130000000, "loi_nhuan_sau_thue": 13000000, "tong_tai_san": 560000000}
            }
        },
        "financial_forecasts": {}
    }

    result = financial_forecasting_node(test_state)
    print(f"Forecast generated: {result['forecast_generated']}")
    if "financial_forecasts" in result:
        for scope, metrics in result["financial_forecasts"].items():
            print(f"Scope: {scope}")
            for metric, forecast_data in metrics.items():
                print(f"  {metric}:")
                print(f"    Historical: {forecast_data['historical_values']}")
                print(f"    Forecast: {forecast_data['point_forecast']}")
                print(f"    80% PI: [{forecast_data['lower_80']}, {forecast_data['upper_80']}]")