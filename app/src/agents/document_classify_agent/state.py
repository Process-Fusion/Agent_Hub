from pydantic import BaseModel, Field
from typing import Annotated, List
from langgraph.graph.message import add_messages
from src.agents.agent_factory import State

class ClassificationAgentState(State):
  classification_type: str = Field(description="The classification type assigned by AI (Invoice, Purchase Order, etc.)")
  confidence_score: float = Field(description="Confidence score of the classification (0.0-1.0)")
  reasoning: str = Field(description="Detailed reasoning for the classification")
  keywords: List[str] = Field(description="The keywords extracted from the document")
  keyword_ids: List[str] = Field(description="The IDs of the keywords extracted from the document")
  document_name: str = Field(description="The name of the document")