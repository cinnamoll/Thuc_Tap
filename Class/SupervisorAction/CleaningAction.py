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
    file_path: Optional[str] = None
    file_format: Optional[str] = None
    reason: Optional[str] = ""
    column: Optional[str] = ""
    rows_affected: Optional[int] = None
    rows_ratio: Optional[float] = None
    risk_level: Optional[Literal["low", "medium", "high"]] = None
    actionType: CleaningActionType
    target_dtype: Optional[str] = None

    @field_validator("column", "reason", mode="before")
    @classmethod
    def convert_none_to_str(cls, value):
        if value is None:
            return ""
        return value

    @field_validator("actionType", mode="before")
    @classmethod
    def map_action_type(cls, value):
        if isinstance(value, str):
            v_lower = value.lower()
            if v_lower in ("fill_missing", "impute", "fillna", "impute_missing"):
                return CleaningActionType.IMPUTE_MODE
            elif v_lower in ("drop", "remove_rows"):
                return CleaningActionType.DROP_ROWS
            elif v_lower in ("drop_col", "remove_column"):
                return CleaningActionType.DROP_COLUMN
            elif v_lower in ("change_dtype", "convert_dtype"):
                return CleaningActionType.CAST_DTYPE
        return value

    @field_validator("target_dtype", mode='after')
    @classmethod
    def require_dtype_for_cast(cls, value, info):
        if info.data.get("actionType") == CleaningActionType.CAST_DTYPE and not value:
            raise ValueError("cast_dtype needs target_dtype")
        return value