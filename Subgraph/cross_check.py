from typing import Any, Dict, List

from Class.FinancialState import FinancialReportState

BS_FIELDS = ("tong_tai_san", "von_chu_so_huu", "no_phai_tra", "tong_nguon_von")
IS_FIELDS = ("doanh_thu", "loi_nhuan_sau_thue")
INFO_FIELDS = set(IS_FIELDS)

def cross_check_scope_node(state: FinancialReportState) -> dict:
    metrics: Dict[str, Dict[str, Dict[str, float]]] = state.get("period_metrics") or {}
    consolidated = metrics.get("consolidated") or {}
    separate = metrics.get("separate") or {}

    recs: List[Dict[str, Any]] = []
    flags: List[Dict[str, Any]] = []

    for period_key in sorted(set(consolidated) | set(separate)):
        cons = consolidated.get(period_key) or {}
        sep = separate.get(period_key) or {}
        for field in BS_FIELDS + IS_FIELDS:
            cv = cons.get(field)
            sv = sep.get(field)
            if cv is None or sv is None:
                continue
            delta = float(cv) - float(sv)
            if abs(delta) < 1.0:
                continue
            if field in INFO_FIELDS:
                severity = "INFO"
            else:
                rel = abs(delta) / max(abs(float(cv)), 1.0)
                severity = "MEDIUM" if rel > 0.5 else "LOW"
            recs.append({
                "period_key": period_key,
                "field": field,
                "consolidated": float(cv),
                "separate": float(sv),
                "delta": delta,
                "severity": severity,
                "message": (
                    f"{period_key}: {field} hợp nhất={float(cv):,.0f} vs riêng={float(sv):,.0f} "
                    f"(lệch {delta:,.0f})"
                ),
            })
            if severity in ("MEDIUM", "HIGH"):
                flags.append({
                    "period_key": period_key,
                    "scope": "consolidated_vs_separate",
                    "flag_type": "scope_divergence",
                    "field": field,
                    "message": recs[-1]["message"],
                    "severity": severity,
                })

    return {"scope_reconciliation": recs, "validation_flags": flags}