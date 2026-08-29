from typing import Annotated, List, Dict, Any, Optional, TypedDict
import operator

from Class.ReportContent.IncomeStatement import IncomeStatement
from Class.ReportContent.FinancialNotesReport import FinancialNotesReport
from Class.ReportContent.CashFlowStatement import CashFlowStatement
from Class.ReportContent.BalanceSheet import BalanceSheet

class AccountingValidationFlag(TypedDict):
    year: int
    flag_type: str  # 'identity_violation' | 'yoy_anomaly'
    field: str
    message: str
    severity: str   # 'HIGH' | 'MEDIUM' | 'LOW'

class FinancialReportState(TypedDict):
    batch_id: str
    input_files: List[str]
    company_name: Optional[str]

    dispatched_tasks: List[Dict[str, Any]]
    income_data: List[IncomeStatement]
    financial_data: List[FinancialNotesReport]
    cash_data: List[CashFlowStatement]
    balance_data: List[BalanceSheet]

    # extracted_data: Annotated[List[Dict[str, Any]], operator.add]

    # Schema Harmonizer — unified & currency-normalised dataset
    harmonized_dataset: Dict[str, Any]
    currency_unit: str  # e.g. 'VND_BILLION'

    # ── Accounting validation ──────────────────────────────────────────────────
    validation_flags: List[AccountingValidationFlag]

    # ── Ratio & Trend Analysis ─────────────────────────────────────────────────
    ratios: Dict[str, Dict[int, float]]   # ratio_name -> {year: value}
    trends: Dict[str, Dict[str, float]]   # metric_name -> {YoY_%, CAGR_%}

    # ── Report output ──────────────────────────────────────────────────────────
    narrative_mda: str
    final_report_md: str
    output_report_path: Optional[str]

    # ── Structured report content (serialized Pydantic models) ────────────────
    balance_sheet_obj: Optional[Dict[str, Any]]
    income_statement_obj: Optional[Dict[str, Any]]
    cash_flow_obj: Optional[Dict[str, Any]]
    notes_obj: Optional[Dict[str, Any]]

