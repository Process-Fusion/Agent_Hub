from pydantic import BaseModel

class DocumentClassifyResponse(BaseModel):
  document_name: str
  classification_type: str
  confidence_score: float
  reasoning: str
  matched_keyword_ids: list[int] = []