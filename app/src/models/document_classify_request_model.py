from pydantic import BaseModel, BeforeValidator
from typing import Annotated, List
import base64

class DocumentClassifyRequest(BaseModel):
  document_name: str
  request: str
  image_bytes: List[str]