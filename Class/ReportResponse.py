from pydantic import BaseModel, Field
from enum import Enum
from typing import List

class FeedbackCategory(str, Enum):
    DATA_ERROR = "data_error"           
    VALIDATION_MISS = "validation_miss" 
    CALC_ERROR = "calc_error"           
    SCOPE_ERROR = "scope_error"       
    NARRATIVE_ONLY = "narrative_only"  
    OUT_OF_SCOPE = "out_of_scope"      

class RejectionAnalysis(BaseModel):
    category: FeedbackCategory
    target_node: str = Field(description="Phải thuộc VALID_TARGET_NODES")
    specific_issue: str       
    affected_fields: List[str] = []
    confidence: float     