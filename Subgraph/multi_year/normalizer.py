from Class.FinancialState import FinancialReportState

ACCOUNTING_TAXONOMY_MAP = {
    "doanh_thu": ["doanh_thu", "doanh_thu_ban_hang", "revenue", "net_revenue", "sales"],
    "loi_nhuan_sau_thue": ["loi_nhuan_sau_thue", "net_profit", "loi_nhuan_st", "pat", "profit_after_tax"],
    "tong_tai_san": ["tong_tai_san", "total_assets", "tong_ts", "assets"],
    "von_chu_so_huu": ["von_chu_so_huu", "owner_equity", "equity", "vcsh"],
    "no_phai_tra": ["no_phai_tra", "total_liabilities", "liabilities", "no_phai_tra"]
}

def schema_mapper(state: FinancialReportState) -> dict:
    """Standardizes account line items across multi-year data into a unified taxonomy schema."""
    long_format = state.get("long_format_dataset", {})
    unified = {}
    
    for year, profile in long_format.items():
        unified[year] = {}
        columns = profile.get("columns", {}) if isinstance(profile, dict) else {}
        
        # Match features/columns to standard taxonomy
        for std_key, aliases in ACCOUNTING_TAXONOMY_MAP.items():
            found_val = None
            for alias in aliases:
                if alias in profile:
                    found_val = profile[alias]
                    break
                elif isinstance(columns, dict) and alias in columns:
                    found_val = columns[alias].get("mean", columns[alias].get("value", 0))
                    break
            
            unified[year][std_key] = float(found_val) if found_val is not None else 0.0
            
    return {"unified_dataset": unified}

def unit_currency_normalizer(state: FinancialReportState) -> dict:
    """Ensures monetary values across all years are scaled to a single unit (VND Billion)."""
    unified = state.get("unified_dataset", {})
    normalized = {}
    
    for year, data in unified.items():
        normalized[year] = {}
        for key, val in data.items():
            # If value is in raw VND (> 1e7), convert to VND Billion (/ 1e9)
            if abs(val) > 1e7:
                normalized[year][key] = round(val / 1e9, 4)
            else:
                normalized[year][key] = round(val, 4)
                
    return {
        "unified_dataset": normalized,
        "currency_unit": "VND_BILLION"
    }
