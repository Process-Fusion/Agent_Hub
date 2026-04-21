from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional, Literal, Union
from datetime import datetime

_KEYWORD_TYPE_MAP = {0: "PRIMARY", 1: "CONTEXTUAL", 2: "ABSENCE", 3: "STRUCTURAL", 4: "SEMANTIC_ALIAS"}
_SOURCE_MAP = {0: "SEED", 1: "AGENT_EXTRACTED", 2: "HUMAN_CORRECTED"}


class ClassificationKeywordModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    KeywordID: int = Field(default=0, alias="keywordid")
    TypeID: int = Field(default=0, alias="typeid")
    ClassificationKeyword: str = Field(default="", alias="classificationkeywords")
    IsActive: bool = Field(default=True, alias="isactive")
    KeywordType: Literal["PRIMARY", "CONTEXTUAL", "ABSENCE", "STRUCTURAL", "SEMANTIC_ALIAS"] = Field(
        default="PRIMARY", alias="keywordtype",
        description=(
            "PRIMARY - Core identifier, strong signal (e.g. 'Invoice', 'Purchase Order')\n"
            "CONTEXTUAL - Must co-exist with primary to validate (e.g. 'Due Date', 'Line Items')\n"
            "ABSENCE - Its absence disproves the type (e.g. 'no invoice number')\n"
            "STRUCTURAL - Document layout fingerprint (e.g. 'line items table')\n"
            "SEMANTIC_ALIAS - Synonym/semantic equivalent (e.g. 'Bill' for Invoice)"
        ),
    )
    Source: Literal["SEED", "AGENT_EXTRACTED", "HUMAN_CORRECTED"] = Field(
        default="SEED", alias="source",
        description=(
            "SEED - Hardcoded at init, high trust, do not remove lightly\n"
            "AGENT_EXTRACTED - LLM-learned, not yet validated by human, lower trust\n"
            "HUMAN_CORRECTED - Came from a human correction event, high trust"
        ),
    )
    KeywordHitCount: int = Field(default=0, alias="keywordhitcount")
    KeywordMissCount: int = Field(default=0, alias="keywordmisscount")
    LastSeenDate: Optional[datetime] = Field(default=None, alias="lastseendate")
    CreatedDate: Optional[datetime] = Field(default=None, alias="createddate")
    ModifiedDate: Optional[datetime] = Field(default=None, alias="modifieddate")

    @field_validator("KeywordType", mode="before")
    @classmethod
    def _coerce_keyword_type(cls, v: Union[int, str]) -> str:
        if isinstance(v, int):
            return _KEYWORD_TYPE_MAP.get(v, "PRIMARY")
        return v

    @field_validator("Source", mode="before")
    @classmethod
    def _coerce_source(cls, v: Union[int, str]) -> str:
        if isinstance(v, int):
            return _SOURCE_MAP.get(v, "SEED")
        return v
