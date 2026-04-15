from pydantic import BaseModel, Field
from typing import Annotated
from langgraph.graph.message import add_messages
from src.agents.agent_factory import State

class ClassificationAgentState(State):
  classification_type: Field(description="The classification type assigned by AI (Invoice, Purchase Order, etc.)")
  confidence_score: Field(description="Confidence score of the classification (0.0-1.0)")
  reasoning: Field(description="Detailed reasoning for the classification")
  keywords: Field(description="The keywords extracted from the document")
  keyword_ids: Field(description="The IDs of the keywords extracted from the document")
  document_name: Field(description="The name of the document")
  document_id: Field(description="The ID of the document")
  document_url: Field(description="The URL of the document")
  document_content: Field(description="The content of the document")
  document_type: Field(description="The type of the document")