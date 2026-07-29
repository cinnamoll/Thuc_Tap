from typing import Annotated, Sequence, List, Optional, TypedDict
from langchain_core.messages import BaseMessage
from operator import add as add_messages

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    cols: Optional[List[str]]
    metadata: Optional[List[str]]
    file_path: str
    file_format: str
    dataset_profile: Optional[dict]
    univariate = Optional[dict]
    
    current_step: Optional[str]
    next_step: Optional[str]
    completed_steps: Optional[List[str]]
    
    risk_level: Optional[str]
    pending_action: Optional[dict]
    computed_impact: Optional[float]
    validation: Optional[bool]
    retry_count: int = 0
    action_status: Optional[bool]    
    fallback_used: bool = False