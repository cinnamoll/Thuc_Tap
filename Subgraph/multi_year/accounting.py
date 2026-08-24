from Class.FinancialState import FinancialReportState, AccountingValidationFlag

def accounting_identity_checker(state: FinancialReportState) -> dict:
    """Validates accounting equations (e.g., Total Assets = Liabilities + Equity)."""
    unified = state.get("unified_dataset", {})
    flags: list[AccountingValidationFlag] = []
    
    for year, data in unified.items():
        assets = data.get("tong_tai_san", 0.0)
        liabilities = data.get("no_phai_tra", 0.0)
        equity = data.get("von_chu_so_huu", 0.0)
        
        if assets > 0 and (liabilities > 0 or equity > 0):
            diff = abs(assets - (liabilities + equity))
            if diff > 1e-2:
                flags.append({
                    "year": year,
                    "flag_type": "identity_violation",
                    "field": "tong_tai_san",
                    "message": f"Balance sheet discrepancy in year {year}: Assets ({assets:.2f}) != Liabilities+Equity ({liabilities+equity:.2f})",
                    "severity": "HIGH"
                })
                
    return {"validation_flags": flags}

def yoy_variance_flagger(state: FinancialReportState) -> dict:
    """Flags sudden year-over-year spikes or drops exceeding threshold (> 50%)."""
    unified = state.get("unified_dataset", {})
    flags = list(state.get("validation_flags", []))
    years = sorted(unified.keys())
    
    for i in range(1, len(years)):
        prev_y, curr_y = years[i-1], years[i]
        for key in ["doanh_thu", "loi_nhuan_sau_thue"]:
            val_prev = unified[prev_y].get(key, 0.0)
            val_curr = unified[curr_y].get(key, 0.0)
            
            if val_prev > 0:
                change_pct = (val_curr - val_prev) / val_prev
                if abs(change_pct) > 0.5:
                    flags.append({
                        "year": curr_y,
                        "flag_type": "yoy_anomaly",
                        "field": key,
                        "message": f"Significant YoY variation in {key} for {curr_y}: {change_pct*100:+.1f}%",
                        "severity": "MEDIUM"
                    })
                    
    return {"validation_flags": flags}
