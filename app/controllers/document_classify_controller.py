# HTTP routes — health and tool API (Twilio/ElevenLabs call these from their dashboards)
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from src.models.document_classify_request_model import DocumentClassifyRequest
from src.models.document_classify_response_model import DocumentClassifyResponse
from src.models.add_classification_type_request_model import AddClassificationTypeRequest

from src.services.postgres_db_service import get_all_classification_types, get_classification_keywords_by_type, add_classification_type

router = APIRouter(prefix="/api/document-classify", tags=["document-classify"])

@router.post("/classify")
async def document_classify(request: DocumentClassifyRequest) -> DocumentClassifyResponse:
  """
  Classify a document into a classification type.
  """
  try:
    # TODO: Implement the document classification logic
    return DocumentClassifyResponse(
      document_name=request.document_name,
      classification_type="Junk",
      confidence_score=0.95,
      reasoning="This is a junk document."
    )
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))

@router.get("/types")
async def get_classification_types() -> list[str]:
  """
  Get all classification types.
  """
  try:
    return await get_all_classification_types()
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))

@router.get("/keywords/{classification_type}")
async def get_classification_keywords(classification_type: str) -> list[str]:
  """
  Get all classification keywords for a given classification type.
  """
  try:
    return await get_classification_keywords_by_type(classification_type)
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))

@router.post("/type")
async def add_classification_type(request: AddClassificationTypeRequest) -> JSONResponse:
  """
  Add a new classification type.
  """
  try:
    await add_classification_type(request.classification_type, request.description)
    return JSONResponse(status_code=200, content={"message": "Classification type added successfully"})
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))
  