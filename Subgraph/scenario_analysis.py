import json
import os
import uuid
from typing import Any, Dict, List, Tuple
from Class.FinancialState import FinancialReportState
from Subgraph.ratio_trend import build_period_dataset, period_sort_key, select_scope

PREDEFINED_STRESS_SCENARIOS: Dict[str, Dict[str, float]] = {
    "recession": {
        "doanh_thu": -20.0,
        "gia_von_hang_ban": -10.0,
    },
    "commodity_shock": {
        "gia_von_hang_ban": 15.0,
    },
    "currency_fluctuation": {
        "no_phai_tra": 10.0,
        "doanh_thu": -5.0,
    },
    "interest_rate_shock": {
        "chi_phi_tai_chinh": 25.0,
    },
}

def apply_percentage_change(value: float, change_percent: float) -> float:
    return round(value * (1.0 + change_percent / 100.0), 2)

def calculate_key_outputs(period_data: Dict[str, float]) -> Dict[str, float]:
    revenue = period_data.get("doanh_thu") or 0.0
    cogs = period_data.get("gia_von_hang_ban") or 0.0
    gross_profit = period_data.get("loi_nhuan_gop") or (revenue - cogs)
    net_income = period_data.get("loi_nhuan_sau_thue") or 0.0
    assets = period_data.get("tong_tai_san") or 0.0
    liabilities = period_data.get("no_phai_tra") or 0.0
    equity = period_data.get("von_chu_so_huu") or 0.0

    return {
        "doanh_thu": revenue,
        "loi_nhuan_gop": gross_profit,
        "loi_nhuan_sau_thue": net_income,
        "gross_margin_%": round((gross_profit / revenue * 100.0), 2) if revenue else 0.0,
        "net_margin_%": round((net_income / revenue * 100.0), 2) if revenue else 0.0,
        "debt_to_equity": round((liabilities / equity), 2) if equity > 0 else 0.0,
    }

def apply_scenario_to_period_data(period_data: Dict[str, float], scenario_modifications: Dict[str, float]) -> Dict[str, float]:
    modified = dict(period_data)
    for field, pct_change in scenario_modifications.items():
        if field in modified:
            modified[field] = apply_percentage_change(modified[field], pct_change)

    # Recalculate derived line items if affected
    rev = modified.get("doanh_thu") or 0.0
    cogs = modified.get("gia_von_hang_ban") or 0.0
    modified["loi_nhuan_gop"] = round(rev - cogs, 2)

    # If COGS or revenue changed, adjust net income accordingly
    orig_rev = period_data.get("doanh_thu") or 0.0
    orig_cogs = period_data.get("gia_von_hang_ban") or 0.0
    orig_net = period_data.get("loi_nhuan_sau_thue") or 0.0
    delta_gp = (rev - cogs) - (orig_rev - orig_cogs)
    modified["loi_nhuan_sau_thue"] = round(orig_net + delta_gp * 0.8, 2)  # assume 20% tax rate

    return modified

def run_what_if_analysis(base_period_data: Dict[str, float], metrics_to_vary: List[str], variation_range: Tuple[float, float] = (-20.0, 20.0), steps: int = 5) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    min_var, max_var = variation_range
    step_size = (max_var - min_var) / max(1, steps - 1)

    for i in range(steps):
        var_pct = min_var + i * step_size
        mod_dict = {field: var_pct for field in metrics_to_vary}
        simulated_data = apply_scenario_to_period_data(base_period_data, mod_dict)
        outputs = calculate_key_outputs(simulated_data)
        results.append({
            "variation_%": round(var_pct, 1),
            "simulated_metrics": simulated_data,
            "key_outputs": outputs,
        })
    return results

def run_predefined_stress_scenarios(base_period_data: Dict[str, float]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    base_outputs = calculate_key_outputs(base_period_data)

    for scenario_name, mods in PREDEFINED_STRESS_SCENARIOS.items():
        simulated = apply_scenario_to_period_data(base_period_data, mods)
        sim_outputs = calculate_key_outputs(simulated)
        deltas = {
            k: round(sim_outputs[k] - base_outputs.get(k, 0.0), 2)
            for k in sim_outputs
        }
        out[scenario_name] = {
            "scenario": scenario_name,
            "modifications": mods,
            "simulated_outputs": sim_outputs,
            "deltas_from_base": deltas,
        }
    return out

def scenario_analysis_node(state: FinancialReportState) -> dict:
    metrics = state.get("period_metrics") or {}
    _scope, fallback = select_scope(metrics)
    dataset = build_period_dataset(metrics) or fallback

    keys = sorted(dataset.keys(), key=period_sort_key)
    if not keys:
        return {"scenarios": {}}

    latest_key = keys[-1]
    latest_data = dataset[latest_key]

    what_if_rev = run_what_if_analysis(latest_data, ["doanh_thu"], variation_range=(-20.0, 20.0), steps=5)
    stress_results = run_predefined_stress_scenarios(latest_data)

    scenarios = {
        "latest_period": latest_key,
        "what_if_revenue": what_if_rev,
        "stress_tests": stress_results,
    }

    # Create temporary directory for scenario analysis data
    batch_id = state.get("batch_id", "unknown")
    temp_dir = os.path.join("temp_data", batch_id)
    os.makedirs(temp_dir, exist_ok=True)

    # Write scenarios to temporary file
    scenarios_file = os.path.join(temp_dir, "scenarios.json")
    with open(scenarios_file, 'w') as f:
        json.dump(scenarios, f, ensure_ascii=False, indent=2)

    return {"scenarios_path": scenarios_file}
