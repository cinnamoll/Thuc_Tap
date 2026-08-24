import os
import matplotlib.pyplot as plt
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_deepseek import ChatDeepSeek
from Class.FinancialState import FinancialReportState

llm = ChatDeepSeek(model="deepseek-v4-flash")

def chart_composer(state: FinancialReportState) -> dict:
    """Generates multi-year financial trend charts and saves image files."""
    ratios = state.get("ratios", {})
    chart_paths = []
    
    os.makedirs("Subgraph_Img", exist_ok=True)
    
    # Chart 1: ROE & ROA multi-year trends
    if "ROE" in ratios and ratios["ROE"]:
        years = list(ratios["ROE"].keys())
        roe_vals = list(ratios["ROE"].values())
        roa_vals = [ratios.get("ROA", {}).get(y, 0.0) for y in years]
        
        plt.figure(figsize=(8, 4))
        plt.plot(years, roe_vals, marker='o', color='blue', label='ROE (%)')
        plt.plot(years, roa_vals, marker='s', color='green', label='ROA (%)')
        plt.title("Multi-Year Profitability Ratios (ROE & ROA)")
        plt.xlabel("Year")
        plt.ylabel("%")
        plt.legend()
        plt.grid(True)
        chart_path = "Subgraph_Img/multi_year_roe_roa.png"
        plt.savefig(chart_path, bbox_inches='tight')
        plt.close()
        chart_paths.append(chart_path)
        
    return {"chart_paths": chart_paths}

def narrative_writer(state: FinancialReportState) -> dict:
    """Uses LLM to synthesize MD&A executive text explaining trends & anomalies."""
    ratios = state.get("ratios", {})
    trends = state.get("trends", {})
    flags = state.get("validation_flags", [])
    
    prompt = f"""
    Hãy viết báo cáo phân tích quản trị (MD&A) chi tiết bằng tiếng Việt dựa trên dữ liệu sau:
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
            HumanMessage(content=prompt)
        ])
        narrative = res.content
    except Exception as e:
        narrative = f"Phân tích MD&A tự động (Fallback): Doanh nghiệp duy trì hoạt động qua các năm. Chi tiết chỉ số: {ratios}. Lỗi kết nối LLM: {str(e)}"
        
    return {"narrative_mda": narrative}

def generate_financial_report(state: FinancialReportState) -> dict:
    """Assembles narrative, tables, and chart paths into markdown document structure."""
    mda = state.get("narrative_mda", "")
    flags = state.get("validation_flags", [])
    charts = state.get("chart_paths", [])
    ratios = state.get("ratios", {})
    trends = state.get("trends", {})
    
    report_content = f"# BÁO CÁO PHÂN TÍCH TÀI CHÍNH ĐA NIÊN\n\n"
    report_content += f"## 1. Phân tích Tường thuật Quản trị (MD&A)\n\n{mda}\n\n"
    
    report_content += f"## 2. Chỉ số Tài chính & Tăng trưởng\n\n"
    report_content += f"### Chỉ số Ratios:\n```json\n{ratios}\n```\n\n"
    report_content += f"### Xu hướng Tăng trưởng (YoY & CAGR):\n```json\n{trends}\n```\n\n"
    
    report_content += f"## 3. Cảnh báo Kế toán & Kiểm tra Nghiệp vụ\n"
    if flags:
        for f in flags:
            report_content += f"- **[{f['severity']}]** Năm {f['year']}: {f['message']}\n"
    else:
        report_content += "Không ghi nhận bất thường kế toán hoặc vi phạm đẳng thức.\n"
        
    report_content += f"\n## 4. Biểu đồ Xu hướng Liên năm\n"
    for img in charts:
        report_content += f"![Chart]({img})\n"
        
    return {"final_report_md": report_content}

def build_financial_report(state: FinancialReportState) -> dict:
    """Writes the markdown document to disk."""
    report_md = state.get("final_report_md", "")
    os.makedirs("example_output", exist_ok=True)
    output_path = "example_output/Bao_Cao_Tai_Chinh_Da_Nien.md"
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report_md)
        
    return {"output_report_path": output_path}
