from typing import Annotated, List, Dict, Any, Optional, TypedDict
import operator

from Class.ReportContent.IncomeStatement import IncomeStatement
from Class.ReportContent.FinancialNotesReport import FinancialNotesReport
from Class.ReportContent.CashFlowStatement import CashFlowStatement
from Class.ReportContent.BalanceSheet import BalanceSheet

class AccountingValidationFlag(TypedDict):
    year: int
    flag_type: str  
    field: str
    message: str
    severity: str 

class FinancialReportState(TypedDict):
    batch_id: str
    input_files: List[str]
    company_name: Optional[str]

    dispatched_tasks: List[Dict[str, Any]]
    income_data: List[IncomeStatement]
    financial_data: List[FinancialNotesReport]
    cash_data: List[CashFlowStatement]
    balance_data: List[BalanceSheet]

    extracted_data: Annotated[List[Dict[str, Any]], operator.add]

    harmonized_dataset: List[Dict[str, Any]]
    narrative_store: List[Dict[str, Any]]
    currency_unit: str = 'VND_BILLION'

    validation_flags: List[AccountingValidationFlag]

    ratios: Dict[str, Dict[int, float]]  
    trends: Dict[str, Dict[str, float]]   

    narrative_mda: str
    final_report_md: str
    output_report_path: Optional[str]

    balance_sheet_obj: Optional[Dict[str, Any]]
    income_statement_obj: Optional[Dict[str, Any]]
    cash_flow_obj: Optional[Dict[str, Any]]
    notes_obj: Optional[Dict[str, Any]]

