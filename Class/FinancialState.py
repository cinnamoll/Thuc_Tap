from typing import Annotated, List, Dict, Any, Optional, TypedDict
from langchain_core.messages import BaseMessage
from operator import add as add_messages
import operator

class YearWorkerInput(TypedDict):
    file_path: str
    year: int
    company_code: Optional[str]

class AccountingValidationFlag(TypedDict):
    year: int
    flag_type: str  # 'identity_violation' | 'yoy_anomaly'
    field: str
    message: str
    severity: str   # 'HIGH' | 'MEDIUM' | 'LOW'

class FinancialReportState(TypedDict):
    run_id: str
    input_files: List[str]
    company_name: Optional[str]
    
    # Module 1: Fan-out tasks per (year, file) & aggregated results from year_worker instances
    dispatched_tasks: List[Dict[str, Any]]
    per_year_results: Annotated[List[Dict[str, Any]], operator.add]
    long_format_dataset: Dict[str, Any]
    
    # Module 2: Schema mapping & normalizations
    unified_dataset: Dict[str, Any]
    currency_unit: str  # e.g., 'VND_BILLION'
    
    # Module 3: Accounting checks & anomaly flags
    validation_flags: List[AccountingValidationFlag]
    
    # Module 4: Ratio and Trend Analysis
    ratios: Dict[str, Dict[int, float]]  # ratio_name -> {year: value}
    trends: Dict[str, Dict[str, float]]  # metric_name -> {YoY_%, CAGR_%}
    
    # Module 5: Narrative & Outputs
    chart_paths: List[str]
    narrative_mda: str
    final_report_md: str
    output_report_path: Optional[str]
    
    messages: Annotated[List[BaseMessage], add_messages]
