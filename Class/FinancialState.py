from operator import add as add_messages
import operator
from typing import Annotated, Any, Dict, List, Literal, Optional, TypedDict

from Class.AgentState import AgentState
from Class.ReportContent.BalanceSheet import BalanceSheet
from Class.ReportContent.CashFlowStatement import CashFlowStatement
from Class.ReportContent.FinancialNotesReport import FinancialNotesReport
from Class.ReportContent.IncomeStatement import IncomeStatement

class AccountingValidationFlag(TypedDict, total=False):
    period_key: str         
    scope: str             
    year: int
    flag_type: str           
    field: str
    message: str
    severity: str           

class FinancialReportState(AgentState, total=False):
    batch_id: str
    input_files: List[str]
    company_name: Optional[str]
    symbol: Optional[str]

    extraction_plan: List[Dict[str, Any]]
    period_index: List[Dict[str, Any]]

    income_data: Annotated[List[IncomeStatement], operator.add]
    financial_data: Annotated[List[FinancialNotesReport], operator.add]
    cash_data: Annotated[List[CashFlowStatement], operator.add]
    balance_data: Annotated[List[BalanceSheet], operator.add]
    extracted_data: Annotated[List[Dict[str, Any]], operator.add]
    balance_sheet_obj: Annotated[List[Dict[str, Any]], operator.add]
    income_statement_obj: Annotated[List[Dict[str, Any]], operator.add]
    cash_flow_obj: Annotated[List[Dict[str, Any]], operator.add]
    notes_obj: Annotated[List[Dict[str, Any]], operator.add]

    narrative_store: List[Dict[str, Any]]
    harmonized_path: Optional[str]
    harmonized_paths: Dict[str, str]
    period_metrics: Dict[str, Dict[str, Dict[str, float]]]
    currency_unit: str

    scope_reconciliation: List[Dict[str, Any]]
    ratios: Dict[str, Dict[str, float]]
    trends: Dict[str, Dict[str, float]]
    chart_map: Dict[str, List[str]]

    narrative_mda: str
    narratives_mda: Dict[str, str]
    final_report_md: str
    final_reports: Dict[str, str]
    rag_report_md: str
    rag_reports: Dict[str, str]
    output_report_path: Optional[str]
    output_report_paths: List[str]
    rag_report_path: Optional[str]
    rag_report_paths: List[str]

    review_status: Optional[str]
    rejection_reason: Optional[str]
    feedback_history: List[Dict[str, Any]]
    feedback_context: Optional[str]
    retry_count: Optional[int]
    max_retries: Optional[int]
    last_feedback_analysis: Optional[Dict[str, Any]]