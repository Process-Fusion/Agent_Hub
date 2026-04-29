from pydantic import BaseModel, BeforeValidator
from typing import Annotated, List
import base64

class FileRequest(BaseModel):
  File_content: List[str]
  File_name: str

class DocumentClassifyRequest(BaseModel):
  document_name: str
  request: str
  File: FileRequest

