from typing import Annotated, Sequence, List, Optional, TypedDict
from langchain_core.messages import BaseMessage
from operator import add as add_messages

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    cols: Optional[List[str]]
    metadata: Optional[List[str]]
    file_path: str
    file_format: str
    current_step: Optional[str]
    next_step: Optional[str]
    completed_steps: Optional[List[str]]
    retry_count: Optional[int]
    fallback_used: Optional[bool]
    requires_approval: Optional[bool]