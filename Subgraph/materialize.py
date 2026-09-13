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

def materialize_dataset(state: FinancialReportState) -> dict:
    rows = list(state.get("harmonized_dataset") or [])
    batch_id = str(state.get("batch_id") or "batch")
    out_dir = os.path.join("example_output", batch_id)
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "harmonized.csv")

    df = pd.DataFrame(rows)
    if df.empty:
        df = pd.DataFrame(columns=CONTRACT_COLUMNS)
    for col in CONTRACT_COLUMNS:
        if col not in df.columns:
            df[col] = None
    ordered = CONTRACT_COLUMNS + [c for c in df.columns if c not in CONTRACT_COLUMNS]
    df = df[ordered]
    if "value" in df.columns:
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df.to_csv(path, index=False)

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
        "harmonized_path": path,
        "file_path": path,
        "file_format": "csv",
        "output_path": out_dir,
        "dataset_profile": profile,
        "currency_unit": currency_unit,
        "chart_paths": [],
        "messages": [
            SystemMessage(content="Bạn là kỹ sư dữ liệu tài chính, làm việc trên bảng long-format."),
            HumanMessage(content=seed),
        ],
    }