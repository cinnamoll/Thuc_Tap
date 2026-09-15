from typing import Any, Dict, List, Optional

from Class.FinancialState import FinancialReportState
from Class.TableExtractor import fold_text, match_pl_field

CODE_MAP: Dict[str, Dict[str, str]] = {
    "balance_sheet": {
        "100": "tai_san_ngan_han",
        "110": "tien",
        "120": "dau_tu_tai_chinh_ngan_han",
        "130": "phai_thu_ngan_han",
        "140": "hang_ton_kho",
        "150": "tai_san_sinh_hoc_ngan_han",
        "200": "tai_san_dai_han",
        "210": "tscd_huu_hinh",
        "220": "tscd_thue_tai_chinh",
        "227": "tscd_vo_hinh",
        "240": "bat_dong_san_dau_tu",
        "250": "tai_san_do_dang_dai_han",
        "260": "dau_tu_tai_chinh_dai_han",
        "280": "tong_tai_san",     
        "300": "no_phai_tra",
        "310": "no_ngan_han",
        "330": "no_dai_han",
        "400": "von_chu_so_huu",
        "440": "tong_nguon_von",
    },
    "income_statement": {
        "01": "doanh_thu",
        "02": "cac_khoan_giam_tru",
        "10": "doanh_thu_thuan",
        "11": "gia_von_hang_ban",
        "20": "loi_nhuan_gop",
        "30": "loi_nhuan_thuan_kd",
        "31": "thu_nhap_khac",
        "32": "chi_phi_khac",
        "40": "loi_nhuan_khac",
        "50": "loi_nhuan_truoc_thue",
        "51": "thue_tndn_hien_hanh",
        "52": "thue_tndn_hoan_lai",
        "60": "loi_nhuan_sau_thue",
        "70": "eps_co_ban",
        "71": "eps_pha_loang",
    },
    "cash_flow": {
        "20": "luu_chuyen_kinh_doanh",
        "30": "luu_chuyen_dau_tu",
        "40": "luu_chuyen_tai_chinh",
        "50": "luu_chuyen_trong_ky",
        "60": "tien_dau_ky",
        "70": "tien_cuoi_ky",
    },
}

PERIOD_METRIC: Dict[str, str] = {
    "balance_sheet": "so_cuoi_ky",
    "income_statement": "ky_nay",
    "cash_flow": "luy_ke_ky_nay",
}

def code_to_name(report_type: str, code: Optional[str], row_label: Optional[str]) -> str:
    code = (code or "").strip()
    label = row_label or ""

    if report_type == "income_statement":
        field = match_pl_field(label, code or None)
        if field:
            return field

    if report_type == "balance_sheet" and code == "270":
        folded = fold_text(label)
        if any(h in folded for h in ("total", "tong")):
            return "tong_tai_san"
        return "tai_san_dai_han_khac"

    mapped = CODE_MAP.get(report_type, {}).get(code)
    if mapped:
        return mapped

    folded = fold_text(label)
    if folded:
        return folded[:60]
    return f"code_{code}" if code else "unknown"

def canonicalize_metrics(state: FinancialReportState) -> dict:
    rows: List[Dict[str, Any]] = list(state.get("harmonized_dataset") or [])
    period_metrics: Dict[str, Dict[str, Dict[str, float]]] = {}

    for row in rows:
        report_type = row.get("report_type") or row.get("statement_type")
        metric = row.get("metric")
        if PERIOD_METRIC.get(report_type) != metric:
            continue
        scope = row.get("scope")
        period_key = row.get("period_key")
        canon = row.get("line_item_canonical")
        value = row.get("value")
        if not scope or not period_key or not canon or value is None:
            continue
        try:
            period_metrics.setdefault(scope, {}).setdefault(period_key, {})[canon] = float(value)
        except (TypeError, ValueError):
            continue

    return {"period_metrics": period_metrics}