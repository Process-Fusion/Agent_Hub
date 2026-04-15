from pydantic import BaseModel
class DocumentClassifyRequest(BaseModel):
  document_name: str
  request: str
  image_bytes: bytes