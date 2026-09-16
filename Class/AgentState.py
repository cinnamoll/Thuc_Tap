from typing import Annotated, Sequence, List, Dict, Any, Optional, TypedDict, Literal, Union
from langchain_core.messages import BaseMessage
from operator import add as add_messages
import operator

from Class.CleaningAction import CleaningAction
from Class.EDAInsight import EDAInsight, dedupe_list
from Class.EngineeringAction import EngineeringAction
from Class.Report import Report

def merge_preview_feature(left: Optional[Union[List[Any], Any]], right: Optional[Union[List[Any], Any]]) -> List[Any]:
    res = []
    for val in (left, right):
        if val is None:
            continue
        if isinstance(val, list):
            res.extend(val)
        else:
            res.append(val)
    return res

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    cols: Optional[List[str]]
    metadata: Optional[List[str]]
    file_path: str
    file_format: str
    run_id:str
    dataset_profile: dict
    statement_type: Optional[Literal["BalanceSheet", "CashFlow", "IncomeStatement", "FinancialNotes"]]
    period: Optional[str]       
    fiscal_year: Optional[int]
    univariate: Annotated[List[dict], operator.add]
    
    action_type: Literal['cleaning', 'engineering', 'insight']
    pending_cleaning: List[CleaningAction]
    pending_insight: List[EDAInsight]
    pending_engineering: List[EngineeringAction]
    preview_feature: Annotated[List[Any], merge_preview_feature]
    chart_paths: Annotated[List[str], dedupe_list] 
    
    cleaning_done: bool
    eda_done: bool
    engineer_done: bool
    
    risk_level: Optional[List[str]]
    reviewed_actions: Optional[List[str]]
    computed_impact: List[dict]
    validation: Optional[bool]
    retry_count: Optional[int]
    action_status: bool   
    fallback_used: Optional[bool] 
    skip_confirm: Optional[bool]
    action_res: Optional[str]
    
    current_action: Union[CleaningAction, EngineeringAction, EDAInsight, None]
    completed_actions: Annotated[Sequence[BaseMessage], add_messages]
    review_decision: Optional[str]
    
    manager_report: Optional[Report]
    pending_question: Optional[str]
    output_path: Optional[str]

    harmonized_dataset: List[Dict[str, Any]]
    validation_flags: List[Dict[str, Any]]