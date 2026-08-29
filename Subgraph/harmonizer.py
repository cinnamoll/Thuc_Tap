from Class.FinancialState import FinancialReportState

ACCOUNTING_TAXONOMY_MAP = {
    "doanh_thu": ["doanh_thu", "doanh_thu_ban_hang", "revenue", "net_revenue", "sales"],
    "loi_nhuan_sau_thue": ["loi_nhuan_sau_thue", "net_profit", "loi_nhuan_st", "pat", "profit_after_tax"],
    "tong_tai_san": ["tong_tai_san", "total_assets", "tong_ts", "assets"],
    "von_chu_so_huu": ["von_chu_so_huu", "owner_equity", "equity", "vcsh"],
    "no_phai_tra": ["no_phai_tra", "total_liabilities", "liabilities"],
}

def map_to_taxonomy(raw_data: dict) -> dict:
    result = {}
    for std_key, aliases in ACCOUNTING_TAXONOMY_MAP.items():
        found_val = None
        for alias in aliases:
            if alias in raw_data:
                found_val = raw_data[alias]
                break
        result[std_key] = float(found_val) if found_val is not None else 0.0
    return result

def normalize_currency(data: dict) -> dict:
    def normalize_currency_value(val: float, threshold: float = 1e7) -> float:
        if abs(val) > threshold:
            return round(val / 1e9, 4)
        return round(val, 4)

    return {key: normalize_currency_value(val) for key, val in data.items()}

def schema_harmonizer(state: FinancialReportState) -> dict:
    extracted = state.get("extracted_data", [])

    sorted_data = sorted(extracted, key=lambda x: x.get("year", 0))
    per_year_raw = {}
    for entry in sorted_data:
        year = entry.get("year")
        if year is not None:
            fin_data = entry.get("financial_data", {})
            if year in per_year_raw:
                per_year_raw[year].update(fin_data)
            else:
                per_year_raw[year] = dict(fin_data)

    normalized = {}
    for year, raw_data in per_year_raw.items():
        mapped = map_to_taxonomy(raw_data)
        normalized[year] = normalize_currency(mapped)

    return {
        "harmonized_dataset": normalized,
        "currency_unit": "VND_BILLION",
    }