from pydantic import field_validator, BaseModel
from typing import Literal, Optional
from enum import Enum

class EncodingType(str, Enum):
    LABEL = "label_encoding" 
    ORDINAL = "ordinal_encoding"
    FREQUENCY = "frequency_encoding"
    ONE_HOT = "one_hot_encoding"
    NONE = "none"

class BinningType(str, Enum):
    EQUAL = "equal_width" 
    QUANTILE = "quantile"
    STANDARD = "standardize"
    NONE = "none"

class FinancialFeatureType(str, Enum):
    DERIVE_GROWTH_RATE = "derive_growth_rate"       
    COMMON_SIZE_TRANSFORM = "common_size_transform"  
    LAG_FEATURE = "lag_feature"                    
    CROSS_STATEMENT_JOIN = "cross_statement_join"     
    NONE = "none"

class EngineeringAction(BaseModel):
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
    actionType: EncodingType | BinningType | FinancialFeatureType
    n_bin: int = 10
    base_item: Optional[str] = None     
    time_column: Optional[str] = None 

    @field_validator("column", "reason", mode="before")
    @classmethod
    def convert_none_to_str(cls, value):
        if value is None:
            return ""
        return value