from Class.FinancialState import FinancialReportState

def check_yoy(curr_year, prev_data: dict, curr_data: dict, fields: list[str] | None = None, threshold: float = 0.5) -> list[dict]:
    """Gắn cờ biến động YoY vượt ngưỡng giữa 2 năm liền kề."""
    if fields is None:
        fields = ["doanh_thu", "loi_nhuan_sau_thue"]

    flags = []
    for key in fields:
        val_prev = prev_data.get(key, 0.0)
        val_curr = curr_data.get(key, 0.0)

        if val_prev > 0:
            change_pct = (val_curr - val_prev) / val_prev
            if abs(change_pct) > threshold:
                flags.append({
                    "year": curr_year,
                    "flag_type": "yoy_anomaly",
                    "field": key,
                    "message": f"Biến động YoY đáng kể {key} năm {curr_year}: {change_pct * 100:+.1f}%",
                    "severity": "MEDIUM",
                })
    return flags

def compute_single_year_ratios(data: dict) -> dict:
    """Tính chỉ số tài chính cho 1 năm: ROE, ROA, Debt/Equity, Net Margin."""
    pat = data.get("loi_nhuan_sau_thue", 0.0)
    equity = data.get("von_chu_so_huu", 0.0)
    assets = data.get("tong_tai_san", 0.0)
    rev = data.get("doanh_thu", 0.0)
    liab = data.get("no_phai_tra", 0.0)

    return {
        "ROE": round((pat / equity) * 100, 2) if equity != 0 else 0.0,
        "ROA": round((pat / assets) * 100, 2) if assets != 0 else 0.0,
        "Debt_to_Equity": round(liab / equity, 2) if equity != 0 else 0.0,
        "Net_Margin": round((pat / rev) * 100, 2) if rev != 0 else 0.0,
    }
    
def compute_multi_year_trends(dataset: dict, fields: list[str] | None = None) -> dict:
    """Tính YoY growth và CAGR qua nhiều năm."""
    if fields is None:
        fields = ["doanh_thu", "loi_nhuan_sau_thue", "tong_tai_san"]

    trends = {}
    years = sorted(dataset.keys())

    if len(years) <= 1:
        return trends

    n_years = years[-1] - years[0]
    for key in fields:
        start_val = dataset[years[0]].get(key, 0.0)
        end_val = dataset[years[-1]].get(key, 0.0)

        if start_val > 0 and n_years > 0 and end_val > 0:
            cagr = ((end_val / start_val) ** (1 / n_years) - 1) * 100
            trends[key] = {"CAGR_%": round(cagr, 2)}
        else:
            trends[key] = {"CAGR_%": 0.0}

        for i in range(1, len(years)):
            prev_y, curr_y = years[i - 1], years[i]
            v_prev = dataset[prev_y].get(key, 0.0)
            v_curr = dataset[curr_y].get(key, 0.0)
            yoy_pct = ((v_curr - v_prev) / v_prev) * 100 if v_prev > 0 else 0.0
            trends[key][f"YoY_{curr_y}_%"] = round(yoy_pct, 2)

    return trends

def ratio_trend_engine(state: FinancialReportState) -> dict:
    """
    Tính chỉ số tài chính, xu hướng, và gắn cờ biến động bất thường.

    Sử dụng utility functions từ:
    - Subgraph/multi_year/analysis.py (ratios, trends)
    - Subgraph/multi_year/accounting.py (yoy anomaly flags)
    """
    harmonized = state.get("harmonized_dataset", {})

    # ── 1. Tính chỉ số tài chính ─────────────────────────────────────────────
    ratios = {"ROE": {}, "ROA": {}, "Debt_to_Equity": {}, "Net_Margin": {}}
    for year, data in harmonized.items():
        yr_ratios = compute_single_year_ratios(data)
        for key in ratios:
            ratios[key][year] = yr_ratios.get(key, 0.0)

    # ── 2. Tính xu hướng tăng trưởng ─────────────────────────────────────────
    trends = compute_multi_year_trends(harmonized)

    # ── 3. Gắn cờ biến động bất thường ───────────────────────────────────────
    flags = list(state.get("validation_flags", []))
    years = sorted(harmonized.keys())
    for i in range(1, len(years)):
        yoy_flags = check_yoy(years[i], harmonized[years[i - 1]], harmonized[years[i]])
        flags.extend(yoy_flags)

    return {
        "ratios": ratios,
        "trends": trends,
        "validation_flags": flags,
    }
