from pydantic import field_validator, BaseModel
from typing import Literal, Optional
from enum import Enum

class CleaningActionType(str, Enum):
    DROP_ROWS = "drop_rows"
    IMPUTE_MEDIAN = "impute_median"
    IMPUTE_MEAN = "impute_mean"
    IMPUTE_MODE = "impute_mode"
    CAST_DTYPE = "cast_dtype"
    DROP_COLUMN = "drop_column"
    NONE = "none"

class CleaningAction(BaseModel):
    file_path: str
    file_format: str
    reason: str
    column: str
    rows_affected: Optional[int] = None
    rows_ratio: Optional[float] = None
    risk_level: Optional[Literal["low", "medium", "high"]] = None
    actionType: CleaningActionType
    target_dtype: str

    @field_validator("target_dtype")
    @classmethod
    def require_dtype_for_cast(cls, v, info):
        if info.data.get("actionType") == CleaningActionType.CAST_DTYPE and not v:
            raise ValueError("cast_dtype needs target_dtype")
        return v