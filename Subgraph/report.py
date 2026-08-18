from dotenv import load_dotenv
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_deepseek import ChatDeepSeek
import json

from Class.AgentState import AgentState
from Class.EDAInsight import EDAInsight 
from Class.Report import Report

load_dotenv()

llm = ChatDeepSeek(model="deepseek-v4-flash")


    
def generate_report_node(state: AgentState) -> dict:
    action = state["current_action"]

    if isinstance(action, EDAInsight): 
        action_type_val = "eda_insight"
        col = action.column
        rows_affected = 0
        rows_affected_pct = 0.0
        reason_val = f"EDA metric analysis for '{col}': {action.metric_value}"
    else: 
        action_type_val = getattr(action.actionType, "value", str(action.actionType)) if hasattr(action, "actionType") else "unknown"
        col = getattr(action, "column", None)
        rows_affected = getattr(action, "rows_affected", 0)
        rows_affected_pct = round(action.rows_ratio, 4) if getattr(action, "rows_ratio", None) else 0
        reason_val = getattr(action, "reason", "")

    risk_lvl = state.get("risk_level", ["low"])
    risk_str = risk_lvl[0] if isinstance(risk_lvl, list) and risk_lvl else "low"

    facts = {
        "action_type": action_type_val,
        "column": col,
        "rows_affected": rows_affected,
        "rows_affected_pct": rows_affected_pct,
        "risk_level": risk_str,
        "reason": reason_val,
        "execution_result": state.get("action_res", ""),
        "fallback_used": state.get("fallback_used", False),
        "retry_count": state.get("retry_count", 0),
        "n_rows_total": state.get("dataset_profile", {}).get("n_rows"),
    }

    system_prompt = SystemMessage(
        content="""
        You are a report-writing assistant for a tech manager. Your SOLE task is to INTERPRET
        the provided figures into concise, clear business language. 
        ABSOLUTELY DO NOT perform your own calculations or derive new figures beyond the provided data. 
        If fallback_used=True, you must clearly state in the report that this section was not analyzed by AI
        but resulted from an automated fallback.
        """
    )

    human_prompt = HumanMessage(content=f"Verified data:\n{json.dumps(facts, ensure_ascii=False)}")

    structured_llm = llm.with_structured_output(Report, method='json_mode')
    report = structured_llm.invoke([system_prompt, human_prompt])

    return {"manager_report": report}

def build_report_file_node(state: AgentState) -> dict:
    report: Report = state["manager_report"]
    fallback_used = state.get("fallback_used", False)

    lines = [
        "EDA pipeline report",
        f"\n Summary\n{report.summary}",
        "\n Hành động đã thực hiện",
    ]
    lines += [f"- {a}" for a in report.actions_taken]

    if report.key_risks_flagged:
        lines.append("\n Key risks")
        lines += [f"- {r}" for r in report.key_risks_flagged]

    chart_paths = []
    action = state.get("current_action")
    if isinstance(action, EDAInsight) and action.chart_paths:
        chart_paths.extend(action.chart_paths)
    
    if state.get("pending_insight"):
        for insight in state["pending_insight"]:
            if getattr(insight, "chart_paths", None):
                for cp in insight.chart_paths:
                    if cp not in chart_paths:
                        chart_paths.append(cp)

    if not chart_paths and state.get("chart_paths"):
        chart_paths = state.get("chart_paths", [])

    if chart_paths: 
        lines.append("\n Biểu đồ phân tích (Visualizations):")
        for path in chart_paths:
            lines.append(f"![Chart]({path})")

    if fallback_used:
        lines.append("\n> This section was created using a fixed template because the AI ​​failed to generate a valid result after multiple attempts.")

    if report.recommendation:
        lines.append(f"\n Recommendation\n{report.recommendation}")

    output_path = f"BT_Thuc_Tap/example_output/report_{state['run_id']}.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return {"report_path": output_path}