"""
Financial validation subgraph for triple-statement validation and ratio plausibility checking.
"""
from typing import Dict, List, Any, Optional, Tuple
import math

from Class.FinancialState import FinancialReportState

DEFAULT_PROFITABILITY_BOUNDS = {"gross_margin": (0.0, 100.0), "net_margin": (-100.0, 100.0), "roe": (-100.0, 200.0), "roa": (-50.0, 50.0)}
DEFAULT_LEVERAGE_BOUNDS = {"debt_to_equity": (0.0, 5.0), "debt_to_assets": (0.0, 1.0)}
DEFAULT_HEALTH_WEIGHTS = {"profitability": 0.4, "leverage": 0.3, "cash_flow": 0.3}


def validate_balance_sheet_identity(period_data: Dict[str, float]) -> Optional[Dict[str, Any]]:
    """
    Validate Balance Sheet identity: Assets = Liabilities + Equity

    Args:
        period_data: Dictionary containing financial line items for a period

    Returns:
        Validation flag if identity violated, None if valid
    """
    assets = period_data.get("tong_tai_san", 0.0) or 0.0
    liabilities = period_data.get("no_phai_tra", 0.0) or 0.0
    equity = period_data.get("von_chu_so_huu", 0.0) or 0.0

    # Also check alternative identity: Assets = Liabilities + Equity (using tong_nguon_von)
    total_liabilities_equity = period_data.get("tong_nguon_von", 0.0) or 0.0

    # Primary check: Assets = Liabilities + Equity
    expected_assets = liabilities + equity
    if assets != 0 or expected_assets != 0:  # Avoid false zero matches
        diff = abs(assets - expected_assets)
        # Allow small tolerance for rounding (0.1% or 1 unit, whichever is larger)
        tolerance = max(1.0, abs(assets) * 0.001)
        if diff > tolerance:
            return {
                "flag_type": "balance_sheet_identity_violation",
                "field": "tong_tai_san",
                "message": f"Bàn cân đối không cân bằng: Tài sản ({assets:,.0f}) != Nợ PT + Vốn CSH ({expected_assets:,.0f}), lệch {diff:,.0f}",
                "severity": "HIGH",
                "expected_value": expected_assets,
                "actual_value": assets,
                "difference": diff
            }

    # Alternative check: Assets = Tổng nguồn vốn
    expected_assets_alt = total_liabilities_equity
    if assets != 0 or expected_assets_alt != 0:
        diff_alt = abs(assets - expected_assets_alt)
        tolerance_alt = max(1.0, abs(assets) * 0.001)
        if diff_alt > tolerance_alt:
            return {
                "flag_type": "balance_sheet_identity_violation_alt",
                "field": "tong_nguon_von",
                "message": f"Bàn cân đối không cân bằng (tổng nguồn vốn): Tài sản ({assets:,.0f}) != Tổng nguồn vốn ({expected_assets_alt:,.0f}), lệch {diff_alt:,.0f}",
                "severity": "HIGH",
                "expected_value": expected_assets_alt,
                "actual_value": assets,
                "difference": diff_alt
            }

    return None


def validate_retained_earnings(period_data: Dict[str, float], prior_period_data: Optional[Dict[str, float]] = None,
                             dividends: Optional[float] = None) -> Optional[Dict[str, Any]]:
    """
    Validate Retained Earnings reconciliation:
    RE End = RE Beginning + Net Income - Dividends

    Args:
        period_data: Current period financial data
        prior_period_data: Prior period financial data (for RE beginning)
        dividends: Dividends paid during period

    Returns:
        Validation flag if reconciliation violated, None if valid
    """
    # This requires access to retained earnings line items which may not be directly available
    # For now, we'll skip this as it requires specific line item mapping
    # In a full implementation, we would map to appropriate retained earnings accounts
    return None


def validate_cash_flow_reconciliation(period_data: Dict[str, float],
                                    prior_period_data: Optional[Dict[str, float]] = None) -> Optional[Dict[str, Any]]:
    """
    Validate Cash Flow reconciliation:
    Change in Cash = Net CF from Operating + Investing + Financing Activities

    Args:
        period_data: Current period financial data
        prior_period_data: Prior period financial data (for cash beginning)

    Returns:
        Validation flag if reconciliation violated, None if valid
    """
    cash_end = period_data.get("tien_cuoi_ky", 0.0) or 0.0
    cash_begin = period_data.get("tien_dau_ky", 0.0) or 0.0

    # If we don't have beginning cash, try to get from prior period
    if cash_begin == 0 and prior_period_data:
        cash_begin = prior_period_data.get("tien_cuoi_ky", 0.0) or 0.0

    cash_change = cash_end - cash_begin

    cf_operating = period_data.get("luu_chuyen_kinh_doanh", 0.0) or 0.0
    cf_investing = period_data.get("luu_chuyen_dau_tu", 0.0) or 0.0
    cf_financing = period_data.get("luu_chuyen_tai_chinh", 0.0) or 0.0

    cf_total = cf_operating + cf_investing + cf_financing

    if cash_change != 0 or cf_total != 0:  # Avoid false zero matches
        diff = abs(cash_change - cf_total)
        # Allow small tolerance for rounding
        tolerance = max(1.0, abs(cash_change) * 0.001, abs(cf_total) * 0.001)
        if diff > tolerance:
            return {
                "flag_type": "cash_flow_reconciliation_violation",
                "field": "luu_chuyen_trong_ky",
                "message": f"Lưu chuyển tiền không zusp khu trù: Thay đổi tiền mặt ({cash_change:,.0f}) != LT HĐKD ({cf_operating:,.0f}) + LT ĐT ({cf_investing:,.0f}) + LT TC ({cf_financing:,.0f}) = {cf_total:,.0f}, lệch {diff:,.0f}",
                "severity": "HIGH",
                "expected_value": cf_total,
                "actual_value": cash_change,
                "difference": diff
            }

    return None


def validate_gross_profit(period_data: Dict[str, float]) -> Optional[Dict[str, Any]]:
    """
    Validate Gross Profit calculation:
    Gross Profit = Revenue - Cost of Goods Sold

    Args:
        period_data: Current period financial data

    Returns:
        Validation flag if calculation violated, None if valid
    """
    revenue = period_data.get("doanh_thu", 0.0) or 0.0
    cogs = period_data.get("gia_von_hang_ban", 0.0) or 0.0
    gross_profit = period_data.get("loi_nhuan_gop", 0.0) or 0.0

    expected_gross_profit = revenue - cogs

    if gross_profit != 0 or expected_gross_profit != 0:  # Avoid false zero matches
        diff = abs(gross_profit - expected_gross_profit)
        # Allow small tolerance for rounding
        tolerance = max(1.0, abs(revenue) * 0.001, abs(cogs) * 0.001)
        if diff > tolerance:
            return {
                "flag_type": "gross_profit_violation",
                "field": "loi_nhuan_gop",
                "message": f"Lợi nhuận gộp không chính xác: Doanh thu ({revenue:,.0f}) - Giá vốn ({cogs:,.0f}) = {expected_gross_profit:,.0f} != LNH{gross_profit:,.0f}, lệch {diff:,.0f}",
                "severity": "HIGH",
                "expected_value": expected_gross_profit,
                "actual_value": gross_profit,
                "difference": diff
            }

    return None


def validate_operating_cash_flow_vs_net_income(period_data: Dict[str, float]) -> Optional[Dict[str, Any]]:
    """
    Validate Operating Cash Flow reasonableness vs Net Income.
    While not an identity, extreme differences warrant investigation.

    Args:
        period_data: Current period financial data

    Returns:
        Validation flag if relationship unreasonable, None if reasonable
    """
    net_income = period_data.get("loi_nhuan_sau_thue", 0.0) or 0.0
    ocf = period_data.get("luu_chuyen_kinh_doanh", 0.0) or 0.0

    # Avoid division by zero
    if abs(net_income) < 0.1:  # Very small net income
        return None

    # Operating cash flow should generally be in the same direction as net income
    # and typically 80-120% of net income for healthy companies
    ratio = ocf / net_income if net_income != 0 else 0

    # Flag if OCF is negative while NI is positive (or vice versa) - suggests quality issues
    if (net_income > 0 and ocf < 0) or (net_income < 0 and ocf > 0):
        return {
            "flag_type": "operating_cash_flow_quality_issue",
            "field": "luu_chuyen_kinh_doanh",
            "message": f"Lưu chuyển tiền từ HĐKD ({ocf:,.0f}) và lợi nhuận sau thuế ({net_income:,.0f}) có dấu相反, chỉ ra vấn đề chất lượng lợi nhuận",
            "severity": "MEDIUM",
            "ocf_value": ocf,
            "net_income_value": net_income,
            "ratio": ratio
        }

    # Flag if ratio is extremely outside reasonable bounds
    if ratio < 0.3 or ratio > 3.0:  # Very loose bounds to avoid false positives
        return {
            "flag_type": "operating_cash_flow_ratio_anomaly",
            "field": "luu_chuyen_kinh_doanh",
            "message": f"Tỷ số lưu chuyển tiền HĐKD / LNST ({ratio:.2f}) ngoài phạm vi bình thường (0.3 - 3.0), có thể chỉ ra vấn đề về chất lượng tiền lũy hoặc chính sách認識",
            "severity": "MEDIUM",
            "ocf_value": ocf,
            "net_income_value": net_income,
            "ratio": ratio
        }

    return None


def validate_profitability_ratios(period_data: Dict[str, float]) -> List[Dict[str, Any]]:
    """
    Validate profitability ratios are within plausible ranges.

    Args:
        period_data: Current period financial data

    Returns:
        List of validation flags for ratio violations
    """
    flags = []

    revenue = period_data.get("doanh_thu", 0.0) or 0.0
    gross_profit = period_data.get("loi_nhuan_gop", 0.0) or 0.0
    net_income = period_data.get("loi_nhuan_sau_thue", 0.0) or 0.0
    assets = period_data.get("tong_tai_san", 0.0) or 0.0
    equity = period_data.get("von_chu_so_huu", 0.0) or 0.0

    # Gross margin: should be between 0% and 100% for most businesses
    if revenue > 0:
        gross_margin = (gross_profit / revenue) * 100
        if gross_margin < 0 or gross_margin > 100:
            flags.append({
                "flag_type": "gross_margin_violation",
                "field": "loi_nhuan_gop",
                "message": f"Lãi gộp ({gross_margin:.1f}%) ngoài phạm vi hợp lý (0% - 100%)",
                "severity": "HIGH",
                "value": gross_margin,
                "expected_range": [0, 100]
            })
        elif gross_margin > 90:  # Warning level for unusually high gross margin
            flags.append({
                "flag_type": "gross_margin_unusually_high",
                "field": "loi_nhuan_gop",
                "message": f"Lãi gộp ({gross_margin:.1f}%) ungewöyn cao, thể có lỗi phân loại",
                "severity": "MEDIUM",
                "value": gross_margin,
                "threshold": 90
            })

    # Net margin: typically between -50% and 50% for most businesses
    if revenue > 0:
        net_margin = (net_income / revenue) * 100
        if net_margin < -100 or net_margin > 100:  # Extreme values
            flags.append({
                "flag_type": "net_margin_extreme",
                "field": "loi_nhuan_sau_thue",
                "message": f"Lãi ròng ({net_margin:.1f}%) ngoài phạm vi cực đoan (-100% - 100%)",
                "severity": "HIGH",
                "value": net_margin,
                "expected_range": [-100, 100]
            })
        elif net_margin < -50 or net_margin > 50:  # Warning level
            flags.append({
                "flag_type": "net_margin_unusual",
                "field": "loi_nhuan_sau_thue",
                "message": f"Lãi ròng ({net_margin:.1f}%) không bình thường",
                "severity": "MEDIUM",
                "value": net_margin,
                "threshold": 50
            })

    # ROE: typically between -50% and 100% for most businesses
    if equity > 0:
        roe = (net_income / equity) * 100
        if roe < -100 or roe > 200:  # Extreme values
            flags.append({
                "flag_type": "roe_extreme",
                "field": "von_chu_so_huu",
                "message": f"ROE ({roe:.1f}%) ngoài phạm vi cực đoan (-100% - 200%)",
                "severity": "HIGH",
                "value": roe,
                "expected_range": [-100, 200]
            })
        elif roe < -50 or roe > 100:  # Warning level
            flags.append({
                "flag_type": "roe_unusual",
                "field": "von_chu_so_huu",
                "message": f"ROE ({roe:.1f}%) không bình thường",
                "severity": "MEDIUM",
                "value": roe,
                "threshold": 100
            })

    # ROA: typically between -20% and 20% for most businesses
    if assets > 0:
        roa = (net_income / assets) * 100
        if roa < -50 or roa > 50:  # Extreme values
            flags.append({
                "flag_type": "roa_extreme",
                "field": "tong_tai_san",
                "message": f"ROA ({roa:.1f}%) ngoài phạm vi cực đoan (-50% - 50%)",
                "severity": "HIGH",
                "value": roa,
                "expected_range": [-50, 50]
            })
        elif roa < -20 or roa > 20:  # Warning level
            flags.append({
                "flag_type": "roa_unusual",
                "field": "tong_tai_san",
                "message": f"ROA ({roa:.1f}%) không bình thường",
                "severity": "MEDIUM",
                "value": roa,
                "threshold": 20
            })

    return flags


def validate_leverage_ratios(period_data: Dict[str, float]) -> List[Dict[str, Any]]:
    """
    Validate leverage ratios are within plausible ranges.

    Args:
        period_data: Current period financial data

    Returns:
        List of validation flags for ratio violations
    """
    flags = []

    liabilities = period_data.get("no_phai_tra", 0.0) or 0.0
    equity = period_data.get("von_chu_so_huu", 0.0) or 0.0
    assets = period_data.get("tong_tai_san", 0.0) or 0.0

    # Debt to Equity: should be >= 0
    if equity > 0:
        debt_to_equity = liabilities / equity
        if debt_to_equity < 0:
            flags.append({
                "flag_type": "debt_to_equity_negative",
                "field": "no_phai_tra",
                "message": f"Tỷ số nợ/vốn chủ sở hữu ({debt_to_equity:.2f}) âm, không có nghĩa financial",
                "severity": "HIGH",
                "value": debt_to_equity
            })
        elif debt_to_equity > 5:  # Warning level for highly leveraged
            flags.append({
                "flag_type": "debt_to_equity_high",
                "field": "no_phai_tra",
                "message": f"Tỷ số nợ/vốn chủ sở hữu ({debt_to_equity:.2f}) cao, thể chỉ ra rủi ro tài chính",
                "severity": "MEDIUM",
                "value": debt_to_equity,
                "threshold": 5
            })

    # Debt to Assets: should be between 0 and 1
    if assets > 0:
        debt_to_assets = liabilities / assets
        if debt_to_assets < 0 or debt_to_assets > 1:
            flags.append({
                "flag_type": "debt_to_assets_violation",
                "field": "no_phai_tra",
                "message": f"Tỷ số nợ/tài sản ({debt_to_assets:.2f}) ngoài phạm vi hợp lý (0 - 1)",
                "severity": "HIGH",
                "value": debt_to_assets,
                "expected_range": [0, 1]
            })
        elif debt_to_assets > 0.8:  # Warning level
            flags.append({
                "flag_type": "debt_to_assets_high",
                "field": "no_phai_tra",
                "message": f"Tỷ số nợ/tài sản ({debt_to_assets:.2f}) cao, thể chỉ ra đòn bẩy tài chính cao",
                "severity": "MEDIUM",
                "value": debt_to_assets,
                "threshold": 0.8
            })

    return flags


def validate_liquidity_ratios(period_data: Dict[str, float]) -> List[Dict[str, Any]]:
    """
    Validate liquidity ratios are within plausible ranges.

    Args:
        period_data: Current period financial data

    Returns:
        List of validation flags for ratio violations
    """
    flags = []

    # This requires current assets and current liabilities line items
    # For now, we'll skip as these specific line items may not be directly mapped
    # In a full implementation, we would extract current assets and current liabilities

    return flags


def calculate_financial_health_score(period_data: Dict[str, float]) -> Dict[str, Any]:
    """
    Calculate composite financial health score and risk level for a given period.
    """
    revenue = float(period_data.get("doanh_thu", 0.0) or 0.0)
    net_income = float(period_data.get("loi_nhuan_sau_thue", 0.0) or 0.0)
    assets = float(period_data.get("tong_tai_san", 0.0) or 0.0)
    equity = float(period_data.get("von_chu_so_huu", 0.0) or 0.0)
    liabilities = float(period_data.get("no_phai_tra", 0.0) or 0.0)
    ocf = float(period_data.get("luu_chuyen_kinh_doanh", 0.0) or 0.0)

    net_margin = (net_income / revenue * 100.0) if revenue != 0 else 0.0
    roe = (net_income / equity * 100.0) if equity != 0 else 0.0
    prof_score = min(100.0, max(0.0, 50.0 + net_margin + (roe * 0.5)))

    debt_to_equity = (liabilities / equity) if equity != 0 else 0.0
    debt_to_assets = (liabilities / assets) if assets != 0 else 0.0
    lev_score = min(100.0, max(0.0, 100.0 - (debt_to_equity * 15.0) - (debt_to_assets * 30.0)))

    ocf_to_ni = (ocf / net_income) if net_income != 0 else 1.0
    cf_score = min(100.0, max(0.0, 50.0 + (ocf_to_ni * 25.0)))

    weights = DEFAULT_HEALTH_WEIGHTS
    composite_score = round(
        weights["profitability"] * prof_score +
        weights["leverage"] * lev_score +
        weights["cash_flow"] * cf_score, 1
    )

    if composite_score >= 75.0:
        risk_level = "Low Risk"
    elif composite_score >= 50.0:
        risk_level = "Moderate Risk"
    elif composite_score >= 30.0:
        risk_level = "High Risk"
    else:
        risk_level = "Critical Risk"

    return {
        "composite_score": composite_score,
        "profitability_score": round(prof_score, 1),
        "leverage_score": round(lev_score, 1),
        "cash_flow_score": round(cf_score, 1),
        "risk_level": risk_level
    }


def financial_validation_node(state: FinancialReportState) -> Dict[str, Any]:
    """
    Main financial validation node that runs all validation checks and health scoring.

    Args:
        state: Current financial report state

    Returns:
        Updated state with validation flags and health scores
    """
    period_metrics = state.get("period_metrics") or {}
    validation_flags = list(state.get("validation_flags") or [])
    health_scores: Dict[str, Dict[str, Any]] = {}

    for scope, periods in period_metrics.items():
        if not isinstance(periods, dict):
            continue

        sorted_periods = dict(sorted(periods.items()))
        period_keys = list(sorted_periods.keys())
        health_scores[scope] = {}

        for i, period_key in enumerate(period_keys):
            period_data = sorted_periods[period_key]
            if not isinstance(period_data, dict):
                continue

            prior_period_data = sorted_periods[period_keys[i-1]] if i > 0 else None

            bs_identity_flag = validate_balance_sheet_identity(period_data)
            if bs_identity_flag:
                bs_identity_flag.update({"period_key": period_key, "scope": scope})
                validation_flags.append(bs_identity_flag)

            cf_reconciliation_flag = validate_cash_flow_reconciliation(period_data, prior_period_data)
            if cf_reconciliation_flag:
                cf_reconciliation_flag.update({"period_key": period_key, "scope": scope})
                validation_flags.append(cf_reconciliation_flag)

            gp_flag = validate_gross_profit(period_data)
            if gp_flag:
                gp_flag.update({"period_key": period_key, "scope": scope})
                validation_flags.append(gp_flag)

            ocf_flag = validate_operating_cash_flow_vs_net_income(period_data)
            if ocf_flag:
                ocf_flag.update({"period_key": period_key, "scope": scope})
                validation_flags.append(ocf_flag)

            profitability_flags = validate_profitability_ratios(period_data)
            leverage_flags = validate_leverage_ratios(period_data)
            liquidity_flags = validate_liquidity_ratios(period_data)

            for flag_list in [profitability_flags, leverage_flags, liquidity_flags]:
                for flag in flag_list:
                    flag.update({"period_key": period_key, "scope": scope})
                    validation_flags.append(flag)

            health_scores[scope][period_key] = calculate_financial_health_score(period_data)

    return {
        "validation_flags": validation_flags,
        "financial_health_score": health_scores,
        "financial_validation_done": True
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
                    "tien_cuoi_ky": 100000000,
                    "tien_dau_ky": 50000000,
                    "luu_chuyen_kinh_doanh": 80000000,
                    "luu_chuyen_dau_tu": -20000000,
                    "luu_chuyen_tai_chinh": -10000000,
                    "doanh_thu": 500000000,
                    "gia_von_hang_ban": 300000000,
                    "loi_nhuan_gop": 200000000,
                    "loi_nhuan_sau_thue": 50000000
                }
            }
        },
        "validation_flags": []
    }

    result = financial_validation_node(test_state)
    print(f"Validation flags: {len(result['validation_flags'])}")
    for flag in result['validation_flags']:
        print(f"- {flag['message']}")