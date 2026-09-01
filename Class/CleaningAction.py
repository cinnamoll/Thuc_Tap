from pydantic import field_validator, BaseModel
from typing import Literal, Optional
from enum import Enum

class CleaningActionType(str, Enum):
    DROP_ROWS = "drop_rows"
    IMPUTE_MEDIAN = "impute_median"
    IMPUTE_MEAN = "impute_mean"
    IMPUTE_MODE = "impute_mode"
    IMPUTE_ZERO = "impute_zero"                     
    CAST_DTYPE = "cast_dtype"
    DROP_COLUMN = "drop_column"
    FIX_OCR_NUMERIC = "fix_ocr_numeric"              
    RECONCILE_IDENTITY = "reconcile_identity"        
    STANDARDIZE_UNIT = "standardize_unit"            
    NONE = "none"

class CleaningAction(BaseModel):
    file_path: Optional[str] = None
    file_format: Optional[str] = None
    reason: Optional[str] = ""
    column: Optional[str] = ""
    line_item_canonical: Optional[str] = None
    statement_type: Optional[str] = None
    period: Optional[str] = None          
    fiscal_year: Optional[int] = None   
    rows_affected: Optional[int] = None
    rows_ratio: Optional[float] = None
    risk_level: Optional[Literal["low", "medium", "high"]] = None
    actionType: CleaningActionType
    target_dtype: Optional[str] = None
    target_unit: Optional[str] = None  

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
            elif v_lower in ("fill_zero", "zero_fill", "impute_0"):
                return CleaningActionType.IMPUTE_ZERO
            elif v_lower in ("fix_ocr", "ocr_fix", "ocr_numeric"):
                return CleaningActionType.FIX_OCR_NUMERIC
            elif v_lower in ("reconcile", "identity_check", "check_identity"):
                return CleaningActionType.RECONCILE_IDENTITY
            elif v_lower in ("unit_convert", "standardize", "normalize_unit"):
                return CleaningActionType.STANDARDIZE_UNIT
        return value

    @field_validator("target_dtype", mode='after')
    @classmethod
    def require_dtype_for_cast(cls, value, info):
        if info.data.get("actionType") == CleaningActionType.CAST_DTYPE and not value:
            raise ValueError("cast_dtype needs target_dtype")
        return value