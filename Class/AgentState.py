from typing import Annotated, Sequence, List, Optional, TypedDict, Dict
from langchain_core.messages import BaseMessage
from operator import add as add_messages

from CleaningAction import CleaningAction
from EDAInsight import EDAInsight
from EngineeringAction import EngineeringAction

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

    pending_cleaning: List[CleaningAction]
    pending_insight: List[EDAInsight]
    pending_engineer: List[EngineeringAction]
    preview_feature: Optional[list]
    
    cleaning_done: bool=False
    eda_done: bool=False
    engineer_done: bool=False
    
    risk_level: Optional[str]
    computed_impact: Optional[float]
    validation: Optional[bool]
    retry_count: Optional[int]
    action_status: Optional[bool]    
    fallback_used: Optional[bool] 
    skip_confirm: Optional[bool]
    action_res: Optional[str]
    
    current_action: Optional[str]
    completed_actions: Annotated[Sequence[BaseMessage], add_messages]
    review_decision: Optional[str]
    
    manager_report: Annotated[Sequence[BaseMessage], add_messages]