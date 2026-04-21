from pydantic import BaseModel
from typing import List
class DocumentClassifyRequest(BaseModel):
  document_name: str
  request: str
  image_bytes: List[bytes]