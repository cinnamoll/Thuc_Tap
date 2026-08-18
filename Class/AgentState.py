from typing import Annotated, Sequence, List, Optional, TypedDict, Literal, Union
from langchain_core.messages import BaseMessage
from operator import add as add_messages

from Class.CleaningAction import CleaningAction
from Class.EDAInsight import EDAInsight
from Class.EngineeringAction import EngineeringAction
from Class.Report import Report

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    cols: Optional[List[str]]
    metadata: Optional[List[str]]
    file_path: str
    file_format: str
    run_id:str
    check_start:bool
    dataset_profile: dict
    univariate: Optional[dict]
    
    action_type: Literal['cleaning', 'engineering', 'insight']
    pending_cleaning: List[CleaningAction]
    pending_insight: List[EDAInsight]
    pending_engineering: List[EngineeringAction]
    preview_feature: Optional[list]
    chart_paths: Annotated[List[str], add_messages] 
    
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