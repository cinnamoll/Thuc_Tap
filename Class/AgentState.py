from typing import Annotated, Sequence, List, Optional, TypedDict, Dict
from langchain_core.messages import BaseMessage
from operator import add as add_messages

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    cols: Optional[List[str]]
    metadata: Optional[List[str]]
    file_path: str
    file_format: str
    run_id:str
    check_start:bool
    dataset_profile: dict
    univariate = Optional[dict]
    
    risk_level: Optional[str]
    pending_action: Optional[str]
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