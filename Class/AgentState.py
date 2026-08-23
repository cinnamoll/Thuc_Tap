from typing import Annotated, Sequence, List, Optional, TypedDict, Literal, Union
from langchain_core.messages import BaseMessage
from operator import add as add_messages
import operator

from Class.CleaningAction import CleaningAction
from Class.EDAInsight import EDAInsight
from Class.EngineeringAction import EngineeringAction
from Class.Report import Report

def dedupe_list(left: Optional[List[str]], right: Optional[List[str]]) -> List[str]:
    if left is None:
        return list(right or [])
    if right is None:
        return list(left)
    seen = set()
    result = []
    for item in list(left) + list(right):
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    cols: Optional[List[str]]
    metadata: Optional[List[str]]
    file_path: str
    file_format: str
    run_id:str
    check_start:bool
    dataset_profile: dict
    univariate: Annotated[List[dict], operator.add]
    
    action_type: Literal['cleaning', 'engineering', 'insight']
    pending_cleaning: List[CleaningAction]
    pending_insight: List[EDAInsight]
    pending_engineering: List[EngineeringAction]
    preview_feature: Optional[list]
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