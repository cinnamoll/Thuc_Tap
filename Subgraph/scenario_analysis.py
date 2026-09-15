"""
Scenario analysis and stress testing subgraph for financial modeling.
"""
from typing import Dict, List, Any, Optional, Tuple
import math
from copy import deepcopy

from Class.FinancialState import FinancialReportState


def apply_percentage_change(value: float, change_percent: float) -> float:
    """
    Apply a percentage change to a value.

    Args:
        value: Base value
        change_percent: Percentage change (e.g., -10 for -10%, 20 for +20%)

    Returns:
        Modified value
    """
    return value * (1 + change_percent / 100.0)


def apply_scenario_to_period_data(period_data: Dict[str, float], 
                                 scenario_modifications: Dict[str, float]) -> Dict[str, float]:
    """
    Apply scenario modifications to period data.

    Args:
        period_data: Original period financial data
        scenario_modifications: Dictionary mapping line item keys to percentage changes

    Returns:
        Modified period data
    """
    modified_data = deepcopy(period_data)
    
    for line_item, percent_change in scenario_modifications.items():
        if line_item in modified_data:
            try:
                original_value = float(modified_data[line_item]) if modified_data[line_item] is not None else 0.0
                modified_data[line_item] = apply_percentage_change(original_value, percent_change)
            except (ValueError, TypeError):
                # If conversion fails, keep original value
                pass
    
    return modified_data


def run_what_if_analysis(base_period_data: Dict[str, float],
                        metrics_to_vary: List[str],
                        variation_range: Tuple[float, float] = (-20.0, 20.0),
                        steps: int = 5) -> Dict[str, Any]:
    """
    Run what-if analysis by varying key metrics.

    Args:
        base_period_data: Base period financial data
        metrics_to_vary: List of line item keys to vary
        variation_range: Tuple of (min_percent, max_percent) for variation
        steps: Number of steps between min and max (including endpoints)

    Returns:
        Dictionary with scenario results
    """
    min_change, max_change = variation_range
    if steps < 2:
        steps = 2
    
    # Generate step values
    step_values = []
    if steps == 2:
        step_values = [min_change, max_change]
    else:
        step_size = (max_change - min_change) / (steps - 1)
        step_values = [min_change + i * step_size for i in range(steps)]
    
    results = {
        "base_case": base_period_data,
        "scenarios": [],
        "metrics_varied": metrics_to_vary,
        "variation_range": variation_range
    }
    
    # For each metric to vary, create scenarios
    for metric in metrics_to_vary:
        metric_scenarios = []
        for change_percent in step_values:
            # Create modification dict for this metric only
            modifications = {metric: change_percent}
            modified_data = apply_scenario_to_period_data(base_period_data, modifications)
            
            # Calculate key outputs
            key_outputs = calculate_key_outputs(modified_data)
            
            metric_scenarios.append({
                "metric": metric,
                "change_percent": change_percent,
                "modified_data": modified_data,
                "key_outputs": key_outputs
            })
        
        results["scenarios"].append({
            "varied_metric": metric,
            "scenarios": metric_scenarios
        })
    
    return results


PREDEFINED_STRESS_SCENARIOS = {
    "recession": {
        "description": "Recession scenario: Revenue down 15%, margins compressed",
        "modifications": {
            "doanh_thu": -15.0,
            "loi_nhuan_gop": -25.0,
            "loi_nhuan_sau_thue": -35.0,
            "luu_chuyen_kinh_doanh": -30.0
        }
    },
    "commodity_shock": {
        "description": "Commodity price shock: COGS up 20%, squeezing margins",
        "modifications": {
            "gia_von_hang_ban": 20.0,
            "loi_nhuan_gop": -15.0,
            "loi_nhuan_sau_thue": -25.0
        }
    },
    "currency_fluctuation": {
        "description": "Currency fluctuation: Export revenue down 10%, import costs up 15%",
        "modifications": {
            "doanh_thu": -10.0,
            "gia_von_hang_ban": 15.0,
            "loi_nhuan_gop": -12.0,
            "loi_nhuan_sau_thue": -20.0
        }
    },
    "interest_rate_shock": {
        "description": "Interest rate shock: Interest expense up 50%",
        "modifications": {
            "loi_nhuan_sau_thue": -20.0,
            "luu_chuyen_tai_chinh": 50.0
        }
    }
}


def run_predefined_stress_scenarios(base_period_data: Dict[str, float]) -> Dict[str, Any]:
    """
    Run predefined stress scenarios.

    Args:
        base_period_data: Base period financial data

    Returns:
        Dictionary with stress scenario results
    """
    stress_scenarios = PREDEFINED_STRESS_SCENARIOS
    
    results = {
        "base_case": base_period_data,
        "stress_scenarios": {}
    }
    
    for scenario_name, scenario_info in stress_scenarios.items():
        modified_data = apply_scenario_to_period_data(
            base_period_data, 
            scenario_info["modifications"]
        )
        
        key_outputs = calculate_key_outputs(modified_data)
        
        results["stress_scenarios"][scenario_name] = {
            "description": scenario_info["description"],
            "modified_data": modified_data,
            "key_outputs": key_outputs,
            "modifications": scenario_info["modifications"]
        }
    
    return results


def calculate_key_outputs(period_data: Dict[str, float]) -> Dict[str, float]:
    """
    Calculate key financial outputs from period data.

    Args:
        period_data: Financial data for a period

    Returns:
        Dictionary of key outputs
    """
    # Extract key line items with safe conversion
    def safe_float(val):
        try:
            return float(val) if val is not None else 0.0
        except (ValueError, TypeError):
            return 0.0
    
    revenue = safe_float(period_data.get("doanh_thu"))
    cogs = safe_float(period_data.get("gia_von_hang_ban"))
    gross_profit = safe_float(period_data.get("loi_nhuan_gop"))
    net_income = safe_float(period_data.get("loi_nhuan_sau_thue"))
    assets = safe_float(period_data.get("tong_tai_san"))
    liabilities = safe_float(period_data.get("no_phai_tra"))
    equity = safe_float(period_data.get("von_chu_so_huu"))
    ocf = safe_float(period_data.get("luu_chuyen_kinh_doanh"))
    
    # Calculate derived metrics
    gross_margin = (gross_profit / revenue * 100) if revenue != 0 else 0.0
    net_margin = (net_income / revenue * 100) if revenue != 0 else 0.0
    roe = (net_income / equity * 100) if equity != 0 else 0.0
    roa = (net_income / assets * 100) if assets != 0 else 0.0
    debt_to_equity = (liabilities / equity * 100) if equity != 0 else 0.0
    debt_to_assets = (liabilities / assets * 100) if assets != 0 else 0.0
    
    return {
        "revenue": revenue,
        "cogs": cogs,
        "gross_profit": gross_profit,
        "net_income": net_income,
        "assets": assets,
        "liabilities": liabilities,
        "equity": equity,
        "ocf": ocf,
        "gross_margin": gross_margin,
        "net_margin": net_margin,
        "roe": roe,
        "roa": roa,
        "debt_to_equity": debt_to_equity,
        "debt_to_assets": debt_to_assets
    }


def scenario_analysis_node(state: FinancialReportState) -> Dict[str, Any]:
    """
    Main scenario analysis node that runs what-if and stress tests.

    Args:
        state: Current financial report state

    Returns:
        Updated state with scenario analysis results
    """
    # Get the harmonized period metrics
    period_metrics = state.get("period_metrics") or {}
    scenario_results = {}
    
    # Use the most recent period as base for scenario analysis
    # Process each scope (consolidated, separate, etc.)
    for scope, periods in period_metrics.items():
        if not isinstance(periods, dict):
            continue
            
        # Sort periods chronologically and get the most recent
        sorted_periods = dict(sorted(periods.items()))
        period_keys = list(sorted_periods.keys())
        
        if not period_keys:
            continue
            
        # Get most recent period data
        most_recent_key = period_keys[-1]
        base_period_data = sorted_periods[most_recent_key]
        
        if not isinstance(base_period_data, dict):
            continue
        
        # Run what-if analysis for key revenue drivers
        metrics_to_vary = ["doanh_thu", "gia_von_hang_ban"]  # Revenue and COGS as key drivers
        what_if_results = run_what_if_analysis(
            base_period_data, 
            metrics_to_vary, 
            variation_range=(-20.0, 20.0), 
            steps=5
        )
        
        # Run predefined stress scenarios
        stress_results = run_predefined_stress_scenarios(base_period_data)
        
        scenario_results[scope] = {
            "base_period": most_recent_key,
            "base_period_data": base_period_data,
            "what_if_analysis": what_if_results,
            "stress_scenarios": stress_results
        }
    
    return {
        "scenario_analysis_results": scenario_results,
        "scenario_analysis_performed": True
    }


# For testing purposes
if __name__ == "__main__":
    # Test data
    test_state = {
        "period_metrics": {
            "consolidated": {
                "2024Q1": {
                    "tong_tai_san": 1000000000,
                    "no_phai_tra": 400000000,
                    "von_chu_so_huu": 600000000,
                    "doanh_thu": 500000000,
                    "gia_von_hang_ban": 300000000,
                    "loi_nhuan_gop": 200000000,
                    "loi_nhuan_sau_thue": 50000000,
                    "luu_chuyen_kinh_doanh": 80000000
                }
            }
        }
    }

    result = scenario_analysis_node(test_state)
    print(f"Scenario analysis performed: {result['scenario_analysis_performed']}")
    if "scenario_analysis_results" in result:
        for scope, results in result["scenario_analysis_results"].items():
            print(f"\nScope: {scope}")
            print(f"Base period: {results['base_period']}")
            print(f"Number of stress scenarios: {len(results['stress_scenarios']['stress_scenarios'])}")
