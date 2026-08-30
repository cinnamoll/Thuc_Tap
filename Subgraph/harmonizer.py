from Class.FinancialState import FinancialReportState

ACCOUNTING_TAXONOMY_MAP = {
    "doanh_thu": ["doanh_thu", "doanh_thu_ban_hang", "revenue", "net_revenue", "sales"],
    "loi_nhuan_sau_thue": ["loi_nhuan_sau_thue", "net_profit", "loi_nhuan_st", "pat", "profit_after_tax"],
    "tong_tai_san": ["tong_tai_san", "total_assets", "tong_ts", "assets"],
    "von_chu_so_huu": ["von_chu_so_huu", "owner_equity", "equity", "vcsh"],
    "no_phai_tra": ["no_phai_tra", "total_liabilities", "liabilities"],
}

def normalize_currency_value(val: float, threshold: float = 1e7) -> float:
    if abs(val) > threshold:
        return round(val / 1e9, 4)
    return round(val, 4)

def schema_harmonizer(state: FinancialReportState) -> dict:
    extracted = state.get("extracted_data", [])

    rows = []
    for entry in extracted:
        year = entry.get("year")
        symbol = entry.get("symbol", "UNKNOWN")
        if year is None:
            continue
            
        fin_data = entry.get("financial_data", {})
        
        for std_key, aliases in ACCOUNTING_TAXONOMY_MAP.items():
            found_val = None
            for alias in aliases:
                if alias in fin_data:
                    found_val = fin_data[alias]
                    break
                    
            value = float(found_val) if found_val is not None else 0.0
            
            unit = "VND"
            if abs(value) > 1e7:
                unit = "billion VND"
            
            norm_value = normalize_currency_value(value)
            
            stmt_type = "Balance Sheet" if std_key in ["tong_tai_san", "von_chu_so_huu", "no_phai_tra"] else "Income Statement"
            
            rows.append({
                "symbol": symbol,
                "year": year,
                "statement_type": stmt_type,
                "line_item_canonical": std_key,
                "value": norm_value,
                "unit": unit,
                "currency": "VND",
                "note_ref": ""
            })

    return {"harmonized_dataset": rows}