from pydantic import BaseModel

class AddClassificationTypeRequest(BaseModel):
  classification_type: str
  description: str = None