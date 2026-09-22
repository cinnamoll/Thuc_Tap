import json
import os
from typing import Any, Dict, List
from Class.FinancialState import FinancialReportState
from Subgraph.ratio_trend import build_period_dataset, period_sort_key, select_scope

DEFAULT_PROFITABILITY_BOUNDS = {
    "gross_margin": (0.0, 100.0),
    "net_margin": (-50.0, 100.0),
    "roe": (-100.0, 200.0),
    "roa": (-50.0, 100.0),
}

DEFAULT_LEVERAGE_BOUNDS = {
    "debt_to_equity": (0.0, 10.0),
    "debt_to_assets": (0.0, 1.0),
}

DEFAULT_HEALTH_WEIGHTS = {
    "profitability": 0.35,
    "liquidity": 0.25,
    "leverage": 0.25,
    "cash_flow": 0.15,
}

def validate_balance_sheet_identity(period_data: Dict[str, float]) -> List[Dict[str, Any]]:
    flags: List[Dict[str, Any]] = []
    assets = period_data.get("tong_tai_san") or 0.0
    liabilities = period_data.get("no_phai_tra") or 0.0
    equity = period_data.get("von_chu_so_huu") or 0.0
    capital = period_data.get("tong_nguon_von") or 0.0

    if assets and (liabilities or equity):
        diff = abs(assets - (liabilities + equity))
        if diff > 1.0:
            flags.append({
                "flag_type": "identity_violation",
                "field": "tong_tai_san",
                "message": f"BCĐKT không cân bằng: Tài sản ({assets:,.0f}) != Nợ ({liabilities:,.0f}) + Vốn ({equity:,.0f}), lệch {diff:,.0f}",
                "severity": "HIGH",
            })

    if capital and (liabilities or equity):
        diff = abs(capital - (liabilities + equity))
        if diff > 1.0:
            flags.append({
                "flag_type": "identity_violation",
                "field": "tong_nguon_von",
                "message": f"BCĐKT không cân bằng: Nguồn vốn ({capital:,.0f}) != Nợ ({liabilities:,.0f}) + Vốn ({equity:,.0f}), lệch {diff:,.0f}",
                "severity": "HIGH",
            })
    return flags

def validate_retained_earnings(period_data: Dict[str, float], prior_period_data: Dict[str, float], dividends: float = 0.0) -> List[Dict[str, Any]]:
    flags: List[Dict[str, Any]] = []
    if not prior_period_data:
        return flags

    re_current = period_data.get("loi_nhuan_sau_thue_chua_phan_phoi") or 0.0
    re_prior = prior_period_data.get("loi_nhuan_sau_thue_chua_phan_phoi") or 0.0
    net_income = period_data.get("loi_nhuan_sau_thue") or 0.0

    if re_current and re_prior and net_income:
        expected = re_prior + net_income - dividends
        diff = abs(re_current - expected)
        if diff > 10.0 and re_current != 0:
            flags.append({
                "flag_type": "retained_earnings_mismatch",
                "field": "loi_nhuan_sau_thue_chua_phan_phoi",
                "message": f"Khớp nối LNST chưa phân phối lệch {diff:,.0f} (Hiện tại: {re_current:,.0f}, Dự kiến: {expected:,.0f})",
                "severity": "MEDIUM",
            })
    return flags

def validate_cash_flow_reconciliation(period_data: Dict[str, float], prior_period_data: Dict[str, float]) -> List[Dict[str, Any]]:
    flags: List[Dict[str, Any]] = []
    cf_operating = period_data.get("luu_chuyen_kinh_doanh") or 0.0
    cf_investing = period_data.get("luu_chuyen_dau_tu") or 0.0
    cf_financing = period_data.get("luu_chuyen_tai_chinh") or 0.0
    cf_net = period_data.get("luu_chuyen_trong_ky") or 0.0
    cash_end = period_data.get("tien_cuoi_ky") or 0.0
    cash_start = period_data.get("tien_dau_ky") or 0.0

    if cf_operating or cf_investing or cf_financing:
        calculated_net = cf_operating + cf_investing + cf_financing
        if cf_net and abs(cf_net - calculated_net) > 1.0:
            flags.append({
                "flag_type": "cash_flow_mismatch",
                "field": "luu_chuyen_trong_ky",
                "message": f"LCTT thuần ({cf_net:,.0f}) không khớp tổng 3 dòng tiền ({calculated_net:,.0f})",
                "severity": "HIGH",
            })

    if cash_end and cash_start and cf_net:
        expected_cash_end = cash_start + cf_net
        if abs(cash_end - expected_cash_end) > 1.0:
            flags.append({
                "flag_type": "cash_reconciliation_mismatch",
                "field": "tien_cuoi_ky",
                "message": f"Tiền cuối kỳ ({cash_end:,.0f}) != Tiền đầu kỳ ({cash_start:,.0f}) + LCTT thuần ({cf_net:,.0f})",
                "severity": "HIGH",
            })
    return flags

def validate_gross_profit(period_data: Dict[str, float]) -> List[Dict[str, Any]]:
    flags: List[Dict[str, Any]] = []
    revenue = period_data.get("doanh_thu") or 0.0
    cogs = period_data.get("gia_von_hang_ban") or 0.0
    gross_profit = period_data.get("loi_nhuan_gop") or 0.0

    if revenue and cogs and gross_profit:
        expected_gp = revenue - cogs
        if abs(gross_profit - expected_gp) > 1.0:
            flags.append({
                "flag_type": "gross_profit_mismatch",
                "field": "loi_nhuan_gop",
                "message": f"Lợi nhuận gộp ({gross_profit:,.0f}) != Doanh thu ({revenue:,.0f}) - Giá vốn ({cogs:,.0f}), lệch {abs(gross_profit - expected_gp):,.0f}",
                "severity": "HIGH",
            })
    return flags

def validate_operating_cash_flow_vs_net_income(period_data: Dict[str, float]) -> List[Dict[str, Any]]:
    flags: List[Dict[str, Any]] = []
    cf_operating = period_data.get("luu_chuyen_kinh_doanh") or 0.0
    net_income = period_data.get("loi_nhuan_sau_thue") or 0.0

    if net_income > 0 and cf_operating < 0:
        flags.append({
            "flag_type": "cash_quality_warning",
            "field": "luu_chuyen_kinh_doanh",
            "message": f"Bất thường chất lượng lợi nhuận: LNST dương ({net_income:,.0f}) nhưng LCTT HĐKD âm ({cf_operating:,.0f})",
            "severity": "MEDIUM",
        })
    return flags

def validate_profitability_ratios(period_data: Dict[str, float]) -> List[Dict[str, Any]]:
    flags: List[Dict[str, Any]] = []
    revenue = period_data.get("doanh_thu") or 0.0
    net_income = period_data.get("loi_nhuan_sau_thue") or 0.0
    gross_profit = period_data.get("loi_nhuan_gop") or 0.0
    equity = period_data.get("von_chu_so_huu") or 0.0

    if revenue and gross_profit:
        gm = (gross_profit / revenue) * 100.0
        low, high = DEFAULT_PROFITABILITY_BOUNDS["gross_margin"]
        if gm < low or gm > high:
            flags.append({
                "flag_type": "plausibility_warning",
                "field": "loi_nhuan_gop",
                "message": f"Biên lợi nhuận gộp bất thường ({gm:.1f}%) ngoài dải ({low}%, {high}%)",
                "severity": "LOW",
            })

    if revenue and net_income:
        nm = (net_income / revenue) * 100.0
        low, high = DEFAULT_PROFITABILITY_BOUNDS["net_margin"]
        if nm < low or nm > high:
            flags.append({
                "flag_type": "plausibility_warning",
                "field": "loi_nhuan_sau_thue",
                "message": f"Biên lợi nhuận ròng bất thường ({nm:.1f}%) ngoài dải ({low}%, {high}%)",
                "severity": "LOW",
            })

    if equity and net_income:
        roe = (net_income / equity) * 100.0
        low, high = DEFAULT_PROFITABILITY_BOUNDS["roe"]
        if roe < low or roe > high:
            flags.append({
                "flag_type": "plausibility_warning",
                "field": "ROE",
                "message": f"ROE bất thường ({roe:.1f}%) ngoài dải ({low}%, {high}%)",
                "severity": "LOW",
            })

    return flags

def validate_leverage_ratios(period_data: Dict[str, float]) -> List[Dict[str, Any]]:
    flags: List[Dict[str, Any]] = []
    liabilities = period_data.get("no_phai_tra") or 0.0
    equity = period_data.get("von_chu_so_huu") or 0.0
    assets = period_data.get("tong_tai_san") or 0.0

    if equity > 0 and liabilities:
        dte = liabilities / equity
        low, high = DEFAULT_LEVERAGE_BOUNDS["debt_to_equity"]
        if dte > high:
            flags.append({
                "flag_type": "high_leverage_warning",
                "field": "no_phai_tra",
                "message": f"Tỷ lệ Nợ/Vốn CSH rất cao ({dte:.2f}) vượt mức an toàn ({high})",
                "severity": "MEDIUM",
            })

    if assets > 0 and liabilities:
        dta = liabilities / assets
        if dta > 0.9:
            flags.append({
                "flag_type": "high_leverage_warning",
                "field": "tong_tai_san",
                "message": f"Tỷ lệ Nợ/Tổng tài sản cao nguy hiểm ({dta * 100:.1f}%)",
                "severity": "HIGH",
            })
    return flags

def validate_liquidity_ratios(period_data: Dict[str, float]) -> List[Dict[str, Any]]:
    flags: List[Dict[str, Any]] = []
    current_assets = period_data.get("tai_san_ngan_han") or 0.0
    current_liabilities = period_data.get("no_ngan_han") or period_data.get("no_phai_tra") or 0.0

    if current_liabilities > 0 and current_assets:
        cr = current_assets / current_liabilities
        if cr < 0.5:
            flags.append({
                "flag_type": "liquidity_warning",
                "field": "tai_san_ngan_han",
                "message": f"Hệ số thanh toán ngắn hạn rất thấp ({cr:.2f} < 0.5)",
                "severity": "HIGH",
            })
    return flags

def calculate_financial_health_score(period_data: Dict[str, float]) -> Dict[str, Any]:
    revenue = period_data.get("doanh_thu") or 0.0
    net_income = period_data.get("loi_nhuan_sau_thue") or 0.0
    equity = period_data.get("von_chu_so_huu") or 0.0
    liabilities = period_data.get("no_phai_tra") or 0.0
    cf_operating = period_data.get("luu_chuyen_kinh_doanh") or 0.0

    # Profitability (35 pts)
    prof_score = 35.0
    if revenue and net_income:
        nm = (net_income / revenue) * 100.0
        if nm < 0:
            prof_score -= 15.0
        elif nm < 5.0:
            prof_score -= 5.0
    if equity and net_income:
        roe = (net_income / equity) * 100.0
        if roe < 0:
            prof_score -= 15.0
        elif roe < 8.0:
            prof_score -= 5.0
    prof_score = max(0.0, prof_score)

    # Leverage (25 pts)
    lev_score = 25.0
    if equity > 0 and liabilities:
        dte = liabilities / equity
        if dte > 3.0:
            lev_score -= 15.0
        elif dte > 1.5:
            lev_score -= 8.0
    elif equity <= 0:
        lev_score = 0.0
    lev_score = max(0.0, lev_score)

    # Liquidity (25 pts)
    liq_score = 25.0
    current_assets = period_data.get("tai_san_ngan_han") or 0.0
    if liabilities and current_assets:
        cr = current_assets / liabilities
        if cr < 1.0:
            liq_score -= 15.0
        elif cr < 1.5:
            liq_score -= 5.0
    liq_score = max(0.0, liq_score)

    # Cash Flow (15 pts)
    cf_score = 15.0
    if cf_operating < 0:
        cf_score -= 10.0
    if net_income > 0 and cf_operating < net_income:
        cf_score -= 5.0
    cf_score = max(0.0, cf_score)

    total_score = round(prof_score + lev_score + liq_score + cf_score, 1)

    if total_score >= 80.0:
        risk_category = "Low Risk"
    elif total_score >= 60.0:
        risk_category = "Moderate Risk"
    elif total_score >= 40.0:
        risk_category = "High Risk"
    else:
        risk_category = "Critical Risk"

    return {
        "total_score": total_score,
        "risk_category": risk_category,
        "components": {
            "profitability": prof_score,
            "leverage": lev_score,
            "liquidity": liq_score,
            "cash_flow": cf_score,
        },
    }

def financial_validation_node(state: FinancialReportState) -> dict:
    metrics = state.get("period_metrics") or {}
    _scope, fallback = select_scope(metrics)
    dataset = build_period_dataset(metrics) or fallback

    flags = list(state.get("validation_flags") or [])
    health_scores: Dict[str, Dict[str, Any]] = {}
    keys = sorted(dataset.keys(), key=period_sort_key)

    for i, period_key in enumerate(keys):
        pdata = dataset[period_key]
        prior_pdata = dataset[keys[i - 1]] if i > 0 else {}

        p_flags = []
        p_flags.extend(validate_balance_sheet_identity(pdata))
        p_flags.extend(validate_retained_earnings(pdata, prior_pdata))
        p_flags.extend(validate_cash_flow_reconciliation(pdata, prior_pdata))
        p_flags.extend(validate_gross_profit(pdata))
        p_flags.extend(validate_operating_cash_flow_vs_net_income(pdata))
        p_flags.extend(validate_profitability_ratios(pdata))
        p_flags.extend(validate_leverage_ratios(pdata))
        p_flags.extend(validate_liquidity_ratios(pdata))

        for flag in p_flags:
            flag["period_key"] = period_key

        flags.extend(p_flags)
        health_scores[period_key] = calculate_financial_health_score(pdata)

    batch_id = state.get("batch_id", "unknown")
    temp_dir = os.path.join("financial_validation_output", batch_id)
    os.makedirs(temp_dir, exist_ok=True)

    validation_flags_file = os.path.join(temp_dir, "validation_flags.json")
    with open(validation_flags_file, 'w') as f:
        json.dump(flags, f, ensure_ascii=False, indent=2)

    health_scores_file = os.path.join(temp_dir, "health_scores.json")
    with open(health_scores_file, 'w') as f:
        json.dump(health_scores, f, ensure_ascii=False, indent=2)

    return {"validation_flags_path": validation_flags_file,"health_scores_path": health_scores_file}