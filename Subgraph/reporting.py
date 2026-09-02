import os
from dotenv import load_dotenv
import matplotlib
import matplotlib.pyplot as plt
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_deepseek import ChatDeepSeek

from Class.FinancialState import FinancialReportState

load_dotenv()
matplotlib.use('Agg')

llm = ChatDeepSeek(model="deepseek-v4-flash")

def plot_roe_roa(ratios: dict, output_dir: str = "Subgraph_Img") -> str | None:
    if "ROE" not in ratios or not ratios["ROE"]:
        return None

    os.makedirs(output_dir, exist_ok=True)
    years = list(ratios["ROE"].keys())
    roe_vals = list(ratios["ROE"].values())
    roa_vals = [ratios.get("ROA", {}).get(y, 0.0) for y in years]

    plt.figure(figsize=(8, 4))
    plt.plot(years, roe_vals, marker='o', color='#2563EB', label='ROE (%)', linewidth=2)
    plt.plot(years, roa_vals, marker='s', color='#16A34A', label='ROA (%)', linewidth=2)
    plt.title("Xu hướng Tỷ suất Sinh lời (ROE & ROA)")
    plt.xlabel("Năm")
    plt.ylabel("%")
    plt.legend()
    plt.grid(True, alpha=0.3)
    chart_path = os.path.join(output_dir, "trend_roe_roa.png")
    plt.savefig(chart_path, bbox_inches='tight', dpi=150)
    plt.close()
    return chart_path

def plot_revenue_profit(harmonized: dict, output_dir: str = "Subgraph_Img") -> str | None:
    if not harmonized:
        return None

    os.makedirs(output_dir, exist_ok=True)
    years = sorted(harmonized.keys())
    rev_vals = [harmonized[y].get("doanh_thu", 0) for y in years]
    pat_vals = [harmonized[y].get("loi_nhuan_sau_thue", 0) for y in years]

    fig, ax1 = plt.subplots(figsize=(8, 4))
    ax1.bar(years, rev_vals, color='#3B82F6', alpha=0.7, label='Doanh thu (tỷ VND)')
    ax1.set_xlabel("Năm")
    ax1.set_ylabel("Doanh thu (tỷ VND)", color='#3B82F6')

    ax2 = ax1.twinx()
    ax2.plot(years, pat_vals, marker='D', color='#EF4444', linewidth=2, label='LNST (tỷ VND)')
    ax2.set_ylabel("Lợi nhuận sau thuế (tỷ VND)", color='#EF4444')

    fig.legend(loc='upper left', bbox_to_anchor=(0.12, 0.95))
    plt.title("Doanh thu & Lợi nhuận sau thuế Liên niên")
    plt.grid(True, alpha=0.3)
    chart_path = os.path.join(output_dir, "trend_revenue_profit.png")
    plt.savefig(chart_path, bbox_inches='tight', dpi=150)
    plt.close()
    return chart_path

def write_narrative_mda(harmonized: dict, ratios: dict, trends: dict, flags: list) -> str:
    prompt = f"""
    Hãy viết báo cáo phân tích quản trị (MD&A) chi tiết bằng tiếng Việt dựa trên dữ liệu sau:
    - Dữ liệu tài chính đã chuẩn hóa (đơn vị: tỷ VND): {harmonized}
    - Các chỉ số tài chính (ROE, ROA, Net Margin, Debt/Equity): {ratios}
    - Tăng trưởng & CAGR: {trends}
    - Cảnh báo & Bất thường kế toán: {flags}

    Yêu cầu:
    1. Đánh giá tổng quan về sức khỏe tài chính và xu hướng doanh thu, lợi nhuận.
    2. Phân tích nguyên nhân biến động và các điểm cảnh báo kế toán.
    3. Đưa ra khuyến nghị ngắn gọn cho ban quản trị.
    """
    try:
        res = llm.invoke([
            SystemMessage(content="Bạn là Chuyên gia Phân tích Tài chính Cao cấp."),
            HumanMessage(content=prompt),
        ])
        return res.content
    except Exception as e:
        return (
            f"Phân tích MD&A tự động (Fallback): Doanh nghiệp duy trì hoạt động qua các năm. "
            f"Chi tiết chỉ số: {ratios}. Lỗi LLM: {e}"
        )
        
def assemble_report_markdown(narrative: str, ratios: dict, trends: dict, flags: list, chart_paths: list) -> str:
    report = "# BÁO CÁO PHÂN TÍCH TÀI CHÍNH ĐA NIÊN\n\n"
    report += f"## 1. Phân tích Tường thuật Quản trị (MD&A)\n\n{narrative}\n\n"

    report += "## 2. Chỉ số Tài chính & Tăng trưởng\n\n"
    report += f"### Chỉ số Ratios:\n```json\n{ratios}\n```\n\n"
    report += f"### Xu hướng Tăng trưởng (YoY & CAGR):\n```json\n{trends}\n```\n\n"

    report += "## 3. Cảnh báo Kế toán & Kiểm tra Nghiệp vụ\n"
    if flags:
        for f in flags:
            report += f"- **[{f['severity']}]** Năm {f['year']}: {f['message']}\n"
    else:
        report += "Không ghi nhận bất thường kế toán hoặc vi phạm đẳng thức.\n"

    report += "\n## 4. Biểu đồ Xu hướng Liên niên\n"
    for img in chart_paths:
        report += f"![Chart]({img})\n"

    return report

def generate_report_node(state: FinancialReportState) -> dict:
    ratios = state.get("ratios", {})
    trends = state.get("trends", {})
    flags = state.get("validation_flags", [])
    harmonized = state.get("harmonized_dataset", {})

    chart_paths = []
    path = plot_roe_roa(ratios)
    if path:
        chart_paths.append(path)
    path = plot_revenue_profit(harmonized)
    if path:
        chart_paths.append(path)

    narrative = write_narrative_mda(harmonized, ratios, trends, flags)
    report = assemble_report_markdown(narrative, ratios, trends, flags, chart_paths)

    return {"narrative_mda": narrative, "final_report_md": report, "chart_paths": chart_paths}


def build_report_node(state: FinancialReportState) -> dict:
    report_md = state.get("final_report_md", "")
    batch_id = state.get("batch_id", "unknown")

    os.makedirs("example_output", exist_ok=True)
    output_path = f"example_output/Bao_Cao_{batch_id}.md"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report_md)

    return {"output_report_path": output_path}
