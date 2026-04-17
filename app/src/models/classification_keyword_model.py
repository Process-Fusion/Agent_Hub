from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime

class ClassificationKeywordModel(BaseModel):
    KeywordID: int = Field(default=0, alias="KeywordID")
    TypeID: int = Field(default=0, alias="TypeID")
    ClassificationKeyword: str = Field(default="", alias="ClassificationKeywords")
    Stage: int = Field(default=1, alias="Stage")
    IsActive: bool = Field(default=True, alias="IsActive")
    KeywordType: Literal["PRIMARY", "CONTEXTUAL", "ABSENCE", "STRUCTURAL", "SEMANTIC_ALIAS"] = Field(
        default="PRIMARY", alias="KeywordType", description=
        "PRIMARY - Core identifier, strong signal (e.g. 'Invoice', 'Purchase Order')\n"
        "CONTEXTUAL - Must co-exist with primary to validate (e.g. 'Due Date', 'Line Items')\n"
        "ABSENCE - Its absence disproves the type (e.g. 'no invoice number')\n"
        "STRUCTURAL - Document layout fingerprint (e.g. 'line items table')\n"
        "SEMANTIC_ALIAS - Synonym/semantic equivalent (e.g. 'Bill' for Invoice)"
    )
    Source: Literal["SEED", "AGENT_EXTRACTED", "HUMAN_CORRECTED"] = Field(
        default="SEED", alias="Source", description=
        "SEED - Hardcoded at init, high trust, do not remove lightly\n"
        "AGENT_EXTRACTED - LLM-learned, not yet validated by human, lower trust\n"
        "HUMAN_CORRECTED - Came from a human correction event, high trust"
    )
    KeywordHitCount: int = Field(default=0, alias="KeywordHitCount")
    KeywordMissCount: int = Field(default=0, alias="KeywordMissCount")
    LastSeenDate: Optional[datetime] = Field(default=None, alias="LastSeenDate")
    IsActive: bool = Field(default=True, alias="IsActive")
    CreatedDate: Optional[datetime] = Field(default=None, alias="CreatedDate")
    ModifiedDate: Optional[datetime] = Field(default=None, alias="ModifiedDate")