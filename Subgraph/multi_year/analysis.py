from Class.FinancialState import FinancialReportState

def ratio_engine(state: FinancialReportState) -> dict:
    """Computes financial ratios: ROE, ROA, Debt/Equity, Net Profit Margin."""
    unified = state.get("unified_dataset", {})
    ratios = {"ROE": {}, "ROA": {}, "Debt_to_Equity": {}, "Net_Margin": {}}
    
    for year, data in unified.items():
        pat = data.get("loi_nhuan_sau_thue", 0.0)
        equity = data.get("von_chu_so_huu", 0.0)
        assets = data.get("tong_tai_san", 0.0)
        rev = data.get("doanh_thu", 0.0)
        liab = data.get("no_phai_tra", 0.0)
        
        ratios["ROE"][year] = round((pat / equity) * 100, 2) if equity != 0 else 0.0
        ratios["ROA"][year] = round((pat / assets) * 100, 2) if assets != 0 else 0.0
        ratios["Debt_to_Equity"][year] = round(liab / equity, 2) if equity != 0 else 0.0
        ratios["Net_Margin"][year] = round((pat / rev) * 100, 2) if rev != 0 else 0.0
        
    return {"ratios": ratios}

def trend_engine(state: FinancialReportState) -> dict:
    """Calculates YoY growth rates and CAGR across multi-year period."""
    unified = state.get("unified_dataset", {})
    trends = {}
    years = sorted(unified.keys())
    
    if len(years) > 1:
        n_years = years[-1] - years[0]
        for key in ["doanh_thu", "loi_nhuan_sau_thue", "tong_tai_san"]:
            start_val = unified[years[0]].get(key, 0.0)
            end_val = unified[years[-1]].get(key, 0.0)
            
            if start_val > 0 and n_years > 0 and end_val > 0:
                cagr = ((end_val / start_val) ** (1 / n_years) - 1) * 100
                trends[key] = {"CAGR_%": round(cagr, 2)}
            else:
                trends[key] = {"CAGR_%": 0.0}
            
            # Calculate YoY for each step
            for i in range(1, len(years)):
                prev_y, curr_y = years[i-1], years[i]
                v_prev = unified[prev_y].get(key, 0.0)
                v_curr = unified[curr_y].get(key, 0.0)
                yoy_pct = ((v_curr - v_prev) / v_prev) * 100 if v_prev > 0 else 0.0
                trends[key][f"YoY_{curr_y}_%"] = round(yoy_pct, 2)
                
    return {"trends": trends}
