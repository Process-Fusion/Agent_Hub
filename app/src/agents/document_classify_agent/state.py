from pydantic import BaseModel, Field
from typing import Annotated, List
from langgraph.graph.message import add_messages
from src.agents.agent_factory import State

class ClassificationAgentState(State):
  classification_type: str = Field(default = "", description="The classification type assigned by AI (Invoice, Purchase Order, etc.)")
  confidence_score: float = Field(default = 0, description="Confidence score of the classification (0.0-1.0)")
  reasoning: str = Field(default = "", description="Detailed reasoning for the classification")
  keywords: List[str] = Field(default = [], description="The keywords extracted from the document")
  keyword_ids: List[str] = Field(default = [], description="The IDs of the keywords extracted from the document")
  document_name: str = Field(description="The name of the document")
  next_step: str = Field(default = None, description="The next step of the workflow")
  trust_routing: str = Field(default = "", description="The trust routing of the workflow")
  human_correction: str = Field(default = "", description="The human correction classification type")
  human_approved: bool = Field(default = False, description="Whether the human has approved the classification")