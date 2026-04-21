from pydantic import BaseModel, Field

class DocumentHumanResponseModel(BaseModel):
    document_name: str = Field(..., description="The name of the document.")
    human_approved: bool = Field(default=False, description="Whether the document has been approved by a human.")
    human_correction: str = Field(default="", description="The human's correction to the document.")
    agent_classification_type: str = Field(default="", description="The classification type from agent.")