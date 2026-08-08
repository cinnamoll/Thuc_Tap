from dotenv import load_dotenv
from typing import Optional
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace
from pydantic import BaseModel, Field
import json

from Class.AgentState import AgentState

load_dotenv()

hf_endpoint = HuggingFaceEndpoint(
    repo_id='Qwen/Qwen2.5-7B-Instruct',
)

llm = ChatHuggingFace(llm=hf_endpoint) 

class ManagerReport(BaseModel):
    summary: str = Field(..., min_length=20, description="Summarization in 2-3 sentences for managers")
    actions_taken: list[str] = Field(..., description="List executed actions in NLP")
    key_risks_flagged: list[str] = Field(default_factory=list)
    requires_manager_attention: bool
    recommendation: Optional[str] = None
    
def generate_report_node(state: AgentState) -> dict:
    action = state["current_action"]

    facts = {
        "action_type": action.actionType.value,
        "column": getattr(action, "column", None),
        "rows_affected": action.rows_affected,
        "rows_affected_pct": round(action.rows_affected_pct, 4) if action.rows_affected_pct else 0,
        "risk_level": state.get("risk_level", "low"),
        "reason": action.reason,
        "execution_result": state.get("action_res", ""),
        "fallback_used": state.get("fallback_used", False),
        "retry_count": state.get("retry_count", 0),
        "n_rows_total": state["dataset_profile"].get("n_rows"),
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

    structured_llm = llm.with_structured_output(ManagerReport)
    report = structured_llm.invoke([system_prompt, human_prompt])

    return {"manager_report": report}

def build_report_file_node(state: AgentState) -> dict:
    report: ManagerReport = state["manager_report"]
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

    if fallback_used:
        lines.append("\n> This section was created using a fixed template because the AI ​​failed to generate a valid result after multiple attempts.")

    if report.recommendation:
        lines.append(f"\n Recommendation\n{report.recommendation}")

    output_path = f"BT_Thuc_Tap/example_output/report_{state['run_id']}.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return {"report_path": output_path}
