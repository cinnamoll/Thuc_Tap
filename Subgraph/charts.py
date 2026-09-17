import os
from typing import Any, Dict, List, Optional
import matplotlib
import matplotlib.pyplot as plt

from Class.FinancialState import FinancialReportState
from Subgraph.ratio_trend import build_period_dataset, period_sort_key, select_scope

matplotlib.use("Agg")

SUBSECTION_TITLES: Dict[str, str] = {
    "1.1": "Quy mô và cơ cấu tài sản",
    "1.2": "Cơ cấu nguồn vốn",
    "1.3": "Thanh khoản và khả năng trả nợ",
    "1.4": "Kết quả kinh doanh",
    "1.5": "Dòng tiền",
}

SHORT_TERM_LOAN_FIELDS = ("vay_ngan_han","vayvanothuetaichinhnganhan", "shorttermloansandfinanceleaseliabilities", "shorttermloanandpayableforfinanceleasing")

def to_billion(value: Any, unit: str = "VND_BILLION") -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    if unit == "VND":
        return number / 1_000_000_000
    if unit == "VND_THOUSAND":
        return number / 1_000_000
    if unit == "VND_MILLION":
        return number / 1_000
    return number

def check_data(dataset: Dict[str, Dict[str, float]], keys: List[str], field: str) -> bool:
    return any((dataset.get(key) or {}).get(field) is not None for key in keys)

def value_series(dataset: Dict[str, Dict[str, float]], keys: List[str], field: str, unit: str = "VND_BILLION") -> List[float]:
    series: List[float] = []
    for key in keys:
        raw = (dataset.get(key) or {}).get(field)
        series.append(to_billion(raw, unit) if raw is not None else 0.0)
    return series

def finish_graphing(fig, path: str) -> str:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fig.savefig(path, bbox_inches="tight", dpi=150)
    plt.close(fig)
    return path

def style_period_axis(ax, keys: List[str]) -> None:
    ax.set_xticks(list(range(len(keys))))
    ax.set_xticklabels(keys, rotation=45)
    ax.grid(True, alpha=0.3, axis="y")

def plot_asset_structure(dataset: Dict[str, Dict[str, float]], keys: List[str], output_path: str, unit: str = "VND_BILLION") -> Optional[str]:
    fields = ("tai_san_ngan_han", "tai_san_dai_han", "tong_tai_san")
    if not any(check_data(dataset, keys, f) for f in fields):
        return None

    short = value_series(dataset, keys, "tai_san_ngan_han", unit)
    long_term = value_series(dataset, keys, "tai_san_dai_han", unit)
    x = list(range(len(keys)))

    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    ax.bar(x, short, label="Tài sản ngắn hạn", color="#3B82F6", alpha=0.8)
    ax.bar(x, long_term, bottom=short, label="Tài sản dài hạn", color="#F59E0B", alpha=0.8)
    if check_data(dataset, keys, "tong_tai_san"):
        ax.plot(x, value_series(dataset, keys, "tong_tai_san", unit),
                marker="o", color="#111827", linewidth=2, label="Tổng tài sản")
    ax.set_title("Quy mô và cơ cấu tài sản theo kỳ")
    ax.set_ylabel("Giá trị (tỷ VND)")
    ax.legend(fontsize=8)
    style_period_axis(ax, keys)

    components = (
        ("tien", "Tiền & tương đương", "#10B981"),
        ("phai_thu_ngan_han", "Phải thu ngắn hạn", "#6366F1"),
        ("hang_ton_kho", "Hàng tồn kho", "#EF4444"),
    )
    base = [0.0] * len(keys)
    has_component = False
    for field, label, color in components:
        if not check_data(dataset, keys, field):
            continue
        has_component = True
        values = value_series(dataset, keys, field, unit)
        ax2.bar(x, values, bottom=base, label=label, color=color, alpha=0.85)
        base = [b + v for b, v in zip(base, values)]
    if has_component:
        residual = [max(s - b, 0.0) for s, b in zip(short, base)]
        ax2.bar(x, residual, bottom=base, label="Tài sản ngắn hạn khác",
                color="#9CA3AF", alpha=0.85)
        ax2.set_title("Cơ cấu tài sản ngắn hạn theo kỳ")
    else:
        ax2.bar(x, short, label="Tài sản ngắn hạn", color="#3B82F6", alpha=0.8)
        ax2.set_title("Tài sản ngắn hạn theo kỳ")
    ax2.set_ylabel("Giá trị (tỷ VND)")
    ax2.legend(fontsize=8)
    style_period_axis(ax2, keys)

    fig.tight_layout()
    return finish_graphing(fig, output_path)

def plot_capital_structure(dataset: Dict[str, Dict[str, float]], keys: List[str], output_path: str, unit: str = "VND_BILLION") -> Optional[str]:
    fields = ("no_phai_tra", "von_chu_so_huu", "tong_nguon_von")
    if not any(check_data(dataset, keys, f) for f in fields):
        return None

    liabilities = value_series(dataset, keys, "no_phai_tra", unit)
    equity = value_series(dataset, keys, "von_chu_so_huu", unit)
    x = list(range(len(keys)))
    width = 0.38

    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.bar([i - width / 2 for i in x], liabilities, width=width,
           label="Nợ phải trả", color="#EF4444", alpha=0.85)
    ax.bar([i + width / 2 for i in x], equity, width=width,
           label="Vốn chủ sở hữu", color="#10B981", alpha=0.85)
    if check_data(dataset, keys, "tong_nguon_von"):
        ax.plot(x, value_series(dataset, keys, "tong_nguon_von", unit),
                marker="o", color="#111827", linewidth=2, label="Tổng nguồn vốn")
    ax.axhline(0, color="#6B7280", linewidth=0.8)
    ax.set_title("Cơ cấu nguồn vốn theo kỳ")
    ax.set_ylabel("Giá trị (tỷ VND)")
    ax.legend(fontsize=8)
    style_period_axis(ax, keys)

    fig.tight_layout()
    return finish_graphing(fig, output_path)

def safe_ratio(numerator: Optional[float], denominator: Optional[float]) -> float:
    if numerator is None or not denominator:
        return 0.0
    return round(float(numerator) / float(denominator), 3)

def plot_liquidity(dataset: Dict[str, Dict[str, float]], keys: List[str], output_path: str, unit: str = "VND_BILLION") -> Optional[str]:
    if not check_data(dataset, keys, "no_ngan_han"):
        return None
    if not (check_data(dataset, keys, "tai_san_ngan_han") or check_data(dataset, keys, "tien")):
        return None

    current_ratio: List[float] = []
    quick_ratio: List[float] = []
    cash_ratio: List[float] = []
    for key in keys:
        data = dataset.get(key) or {}
        current_liabilities = data.get("no_ngan_han")
        current_assets = data.get("tai_san_ngan_han")
        cash = data.get("tien")
        receivable = data.get("phai_thu_ngan_han")
        current_ratio.append(safe_ratio(current_assets, current_liabilities))
        quick_ratio.append(safe_ratio(
            (cash or 0.0) + (receivable or 0.0) if (cash is not None or receivable is not None) else None,
            current_liabilities,
        ))
        cash_ratio.append(safe_ratio(cash, current_liabilities))

    x = list(range(len(keys)))
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(14, 4.8))

    ax.plot(x, current_ratio, marker="o", color="#3B82F6", linewidth=2, label="Hệ số thanh toán ngắn hạn")
    ax.plot(x, quick_ratio, marker="s", color="#F59E0B", linewidth=2, label="Hệ số thanh toán nhanh")
    ax.plot(x, cash_ratio, marker="^", color="#EF4444", linewidth=2, label="Tiền / Nợ ngắn hạn")
    ax.axhline(1.0, color="#6B7280", linestyle="--", linewidth=1, label="Ngưỡng 1.0")
    ax.set_title("Hệ số thanh khoản theo kỳ")
    ax.set_ylabel("Lần")
    ax.legend(fontsize=8)
    style_period_axis(ax, keys)

    x_bar = list(range(len(keys)))
    width = 0.38
    ax2.bar([i - width / 2 for i in x_bar], value_series(dataset, keys, "no_ngan_han", unit),
            width=width, label="Nợ ngắn hạn", color="#EF4444", alpha=0.85)
    if check_data(dataset, keys, "no_dai_han"):
        ax2.bar([i + width / 2 for i in x_bar], value_series(dataset, keys, "no_dai_han", unit),
                width=width, label="Nợ dài hạn", color="#8B5CF6", alpha=0.85)
        
    loan_field = None
    for field in SHORT_TERM_LOAN_FIELDS:
        if check_data(dataset, keys, field):
            loan_field = field

    if loan_field:
        ax2.plot(x_bar, value_series(dataset, keys, loan_field, unit), marker="D",
                 color="#111827", linewidth=2, label="Vay & nợ thuê TC ngắn hạn")
    ax2.set_title("Cơ cấu nợ phải trả theo kỳ")
    ax2.set_ylabel("Giá trị (tỷ VND)")
    ax2.legend(fontsize=8)
    style_period_axis(ax2, keys)

    fig.tight_layout()
    return finish_graphing(fig, output_path)

def plot_profitability(dataset: Dict[str, Dict[str, float]], keys: List[str], ratios: Dict[str, Dict[str, float]], output_path: str, unit: str = "VND_BILLION") -> Optional[str]:
    income_fields = ("doanh_thu", "gia_von_hang_ban", "loi_nhuan_gop", "loi_nhuan_truoc_thue", "loi_nhuan_sau_thue")
    if not any(check_data(dataset, keys, f) for f in income_fields):
        return None

    x = list(range(len(keys)))
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(14, 4.8))

    bar_specs = (
        ("doanh_thu", "Doanh thu", "#3B82F6"),
        ("gia_von_hang_ban", "Giá vốn hàng bán", "#F97316"),
        ("loi_nhuan_gop", "Lợi nhuận gộp", "#10B981"),
    )
    active_bars = [spec for spec in bar_specs if check_data(dataset, keys, spec[0])]
    width = 0.8 / max(len(active_bars), 1)
    for index, (field, label, color) in enumerate(active_bars):
        offset = (index - (len(active_bars) - 1) / 2) * width
        ax.bar([i + offset for i in x], value_series(dataset, keys, field, unit),
               width=width, label=label, color=color, alpha=0.85)
    for field, label, color in (("loi_nhuan_truoc_thue", "Lợi nhuận trước thuế", "#8B5CF6"),
                                ("loi_nhuan_sau_thue", "Lợi nhuận sau thuế", "#EF4444")):
        if check_data(dataset, keys, field):
            ax.plot(x, value_series(dataset, keys, field, unit),
                    marker="o", color=color, linewidth=2, label=label)
    ax.axhline(0, color="#6B7280", linewidth=0.8)
    ax.set_title("Kết quả kinh doanh theo kỳ")
    ax.set_ylabel("Giá trị (tỷ VND)")
    ax.legend(fontsize=8)
    style_period_axis(ax, keys)

    ratio_specs = (("Net_Margin", "Net Margin (%)", "#3B82F6"),
                   ("ROA", "ROA (%)", "#F59E0B"),
                   ("ROE", "ROE (%)", "#10B981"))
    has_ratio = False
    for name, label, color in ratio_specs:
        series = (ratios or {}).get(name) or {}
        if any(series.get(key) is not None for key in keys):
            has_ratio = True
            ax2.plot(x, [series.get(key) or 0.0 for key in keys],
                     marker="o", color=color, linewidth=2, label=label)
    if not has_ratio:
        ax2.text(0.5, 0.5, "Không có chỉ số sinh lời", ha="center", va="center", transform=ax2.transAxes)
    ax2.axhline(0, color="#6B7280", linewidth=0.8)
    ax2.set_title("Chỉ số sinh lời theo kỳ")
    ax2.set_ylabel("%")
    ax2.legend(fontsize=8)
    style_period_axis(ax2, keys)

    fig.tight_layout()
    return finish_graphing(fig, output_path)

def plot_cashflow(dataset: Dict[str, Dict[str, float]], keys: List[str], output_path: str, unit: str = "VND_BILLION") -> Optional[str]:
    fields = ("luu_chuyen_kinh_doanh", "luu_chuyen_dau_tu", "luu_chuyen_tai_chinh", "luu_chuyen_trong_ky", "tien_cuoi_ky")
    if not any(check_data(dataset, keys, f) for f in fields):
        return None

    x = list(range(len(keys)))
    fig, ax = plt.subplots(figsize=(10, 4.8))

    bar_specs = (
        ("luu_chuyen_kinh_doanh", "Lưu chuyển tiền HĐKD", "#3B82F6"),
        ("luu_chuyen_dau_tu", "Lưu chuyển tiền đầu tư", "#F59E0B"),
        ("luu_chuyen_tai_chinh", "Lưu chuyển tiền tài chính", "#8B5CF6"),
    )
    active_bars = [spec for spec in bar_specs if check_data(dataset, keys, spec[0])]
    width = 0.8 / max(len(active_bars), 1)
    for index, (field, label, color) in enumerate(active_bars):
        offset = (index - (len(active_bars) - 1) / 2) * width
        ax.bar([i + offset for i in x], value_series(dataset, keys, field, unit),
               width=width, label=label, color=color, alpha=0.85)
    if check_data(dataset, keys, "luu_chuyen_trong_ky"):
        ax.plot(x, value_series(dataset, keys, "luu_chuyen_trong_ky", unit),
                marker="o", color="#EF4444", linewidth=2, label="Lưu chuyển tiền thuần")
    ax.axhline(0, color="#6B7280", linewidth=0.8)
    ax.set_title("Dòng tiền theo kỳ")
    ax.set_ylabel("Giá trị (tỷ VND)")
    style_period_axis(ax, keys)

    if check_data(dataset, keys, "tien_cuoi_ky"):
        ax2 = ax.twinx()
        ax2.plot(x, value_series(dataset, keys, "tien_cuoi_ky", unit), marker="s",
                 color="#10B981", linestyle="--", linewidth=2, label="Tiền cuối kỳ")
        ax2.set_ylabel("Tiền cuối kỳ (tỷ VND)", color="#10B981")
        handles1, labels1 = ax.get_legend_handles_labels()
        handles2, labels2 = ax2.get_legend_handles_labels()
        ax.legend(handles1 + handles2, labels1 + labels2, fontsize=8, loc="best")
    else:
        ax.legend(fontsize=8, loc="best")

    fig.tight_layout()
    return finish_graphing(fig, output_path)

def build_financial_charts(dataset: Dict[str, Dict[str, float]], ratios: Dict[str, Dict[str, float]], output_dir: str, unit: str = "VND_BILLION") -> Dict[str, List[str]]:
    keys = sorted((dataset or {}).keys(), key=period_sort_key)
    if not keys:
        return {}
    os.makedirs(output_dir, exist_ok=True)

    builders = (
        ("1.1", "chart_1_1_asset_structure.png",
         lambda path: plot_asset_structure(dataset, keys, path, unit)),
        ("1.2", "chart_1_2_capital_structure.png",
         lambda path: plot_capital_structure(dataset, keys, path, unit)),
        ("1.3", "chart_1_3_liquidity.png",
         lambda path: plot_liquidity(dataset, keys, path, unit)),
        ("1.4", "chart_1_4_profitability.png",
         lambda path: plot_profitability(dataset, keys, ratios, path, unit)),
        ("1.5", "chart_1_5_cashflow.png",
         lambda path: plot_cashflow(dataset, keys, path, unit)),
    )

    chart_map: Dict[str, List[str]] = {}
    for section, filename, builder in builders:
        try:
            path = builder(os.path.join(output_dir, section, filename))
        except Exception: 
            path = None
        if path:
            chart_map[section] = [path]
    return chart_map

def build_charts_node(state: FinancialReportState) -> dict:
    metrics = state.get("period_metrics") or {}
    _scope, fallback = select_scope(metrics)
    dataset = build_period_dataset(metrics) or fallback
    unit = state.get("currency_unit") or "VND_BILLION"
    batch_id = str(state.get("batch_id") or "batch")
    out_dir = os.path.join("example_output", batch_id, "charts")

    chart_map = build_financial_charts(dataset, state.get("ratios") or {}, out_dir, unit)
    paths = [path for section_paths in chart_map.values() for path in section_paths]
    return {"chart_paths": paths, "chart_map": chart_map}