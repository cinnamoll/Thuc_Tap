from pydantic import BaseModel, Field
from typing import Optional

class Report(BaseModel):
    summary: str = Field(..., min_length=20, description="Summarization in 2-3 sentences for managers")
    actions_taken: list[str] = Field(..., description="List executed actions in NLP")
    key_risks_flagged: list[str] = Field(default_factory=list)
    requires_manager_attention: bool
    recommendation: Optional[str] = None