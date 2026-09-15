import os
from typing import Any, Dict, List
import pandas as pd
from langchain_core.messages import HumanMessage, SystemMessage

from Class.FinancialState import FinancialReportState

CONTRACT_COLUMNS: List[str] = [
    "batch_id", "source_file", "symbol", "scope", "lang",
    "statement_type", "report_type",
    "period_key", "period", "fiscal_year", "year",
    "note_id", "note_title", "note_type",
    "row_label", "code", "line_item_canonical",
    "metric", "value", "source_page",
]

def profile_dataframe(df: pd.DataFrame) -> Dict[str, Any]:
    stats: Dict[str, Any] = {}
    for col in df.columns:
        stats[f"{col}_nulls"] = int(df[col].isna().sum())
        stats[f"{col}_nunique"] = int(df[col].nunique(dropna=True))
    return {
        "columns": df.columns.tolist(),
        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
        "stats": stats,
        "n_rows": int(len(df)),
    }

def write_contract_csv(df: pd.DataFrame, path: str) -> str:
    out = df.copy()
    for col in CONTRACT_COLUMNS:
        if col not in out.columns:
            out[col] = None
    ordered = CONTRACT_COLUMNS + [c for c in out.columns if c not in CONTRACT_COLUMNS]
    out = out[ordered]
    if "value" in out.columns:
        out["value"] = pd.to_numeric(out["value"], errors="coerce")
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    out.to_csv(path, index=False)
    return path

def materialize_dataset(state: FinancialReportState) -> dict:
    rows = list(state.get("harmonized_dataset") or [])
    batch_id = str(state.get("batch_id") or "batch")
    out_dir = os.path.join("example_output", batch_id)
    os.makedirs(out_dir, exist_ok=True)

    df = pd.DataFrame(rows)
    if df.empty:
        df = pd.DataFrame(columns=CONTRACT_COLUMNS)

    period_keys: List[str] = []
    if "period_key" in df.columns:
        period_keys = sorted({str(p) for p in df["period_key"].dropna().unique() if str(p)})

    harmonized_paths: Dict[str, str] = {}
    if period_keys:
        for period_key in period_keys:
            period_df = df[df["period_key"].astype(str) == period_key]
            harmonized_paths[period_key] = write_contract_csv(period_df, os.path.join(out_dir, period_key, "harmonized.csv"))
    else:
        harmonized_paths["UNKNOWN"] = write_contract_csv(df, os.path.join(out_dir, "UNKNOWN", "harmonized.csv"))

    if str(state.get("analysis_mode") or "") == "agent":
        work_dir = os.path.join(out_dir, "_work")
        shared_path = write_contract_csv(df, os.path.join(work_dir, "harmonized_all.csv"))
        output_path = work_dir
    else:
        shared_path = next(iter(harmonized_paths.values()))
        output_path = out_dir

    profile = profile_dataframe(df)
    periods = sorted({str(r.get("period_key")) for r in rows if r.get("period_key")})
    scopes = sorted({str(r.get("scope")) for r in rows if r.get("scope")})
    units = [str(item.get("unit")) for item in (state.get("extraction_plan") or []) if item.get("unit")]
    currency_unit = max(set(units), key=units.count) if units else "VND"
    seed = (
        f"Bảng long-format báo cáo tài chính của {state.get('symbol') or 'doanh nghiệp'}.\n"
        f"Cột giá trị số: 'value'. Nhóm chỉ tiêu: 'line_item_canonical'. "
        f"Cột kỳ: 'period' (định dạng NAMQn, ví dụ 2026Q2). Phạm vi: 'scope' ({', '.join(scopes) or 'n/a'}).\n"
        f"Các kỳ hiện có: {', '.join(periods) or 'n/a'}.\n"
        f"Mục tiêu: kiểm tra chất lượng dữ liệu và chuẩn bị cho bước tính chỉ số + lập báo cáo."
    )

    return {
        "harmonized_path": shared_path,
        "harmonized_paths": harmonized_paths,
        "file_path": shared_path,
        "file_format": "csv",
        "output_path": output_path,
        "dataset_profile": profile,
        "currency_unit": currency_unit,
        "chart_paths": [],
        "messages": [
            SystemMessage(content="Bạn là kỹ sư dữ liệu tài chính, làm việc trên bảng long-format."),
            HumanMessage(content=seed),
        ],
    }