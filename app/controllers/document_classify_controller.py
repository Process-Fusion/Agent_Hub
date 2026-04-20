# HTTP routes — health and tool API (Twilio/ElevenLabs call these from their dashboards)
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)
from src.models.document_classify_request_model import DocumentClassifyRequest
from src.models.document_classify_response_model import DocumentClassifyResponse
from src.models.add_classification_type_request_model import AddClassificationTypeRequest
from src.models.document_human_response_model import DocumentHumanResponseModel
from typing import List

from src.services.postgres_db_service import get_all_classification_types, get_classification_keywords_by_type, add_classification_type, deactivate_stale_classification_keywords

router = APIRouter(prefix="/api/document-classify", tags=["document-classify"])

@router.post("/classify")
async def document_classify(request: DocumentClassifyRequest) -> DocumentClassifyResponse:
  """
  Classify a document into a classification type.
  """
  try:
    # TODO: Take the agent out and start the conversation, If human needed to be involved in the conversation
    # We still going to send back the response, but will not skill the thread until API human response called
    # and resume the conversation, then after that the thread id will be killed.
    # If human response is not needed, then we will kill the thread after the response is sent.
    return DocumentClassifyResponse(
      document_name=request.document_name,
      classification_type="Junk",
      confidence_score=0.95,
      reasoning="This is a junk document."
    )
  except Exception as e:
    logger.exception(e)
    raise HTTPException(status_code=500, detail=str(e))

@router.post("/humanresponse")
async def document_human_response(human_responses: List[DocumentHumanResponseModel]) -> None:
  """
  Resume the conversation to finish agent workflow that executed during /classify api call.
  The conversation session is stored in postgres db, and is stored with the same name as document name.
  """
  try:
    # TODO: Take agent out and resume the conversation
    for human_response in human_responses:
      pass
      #await resume_conversation(human_response.document_name, human_response)
  except Exception as e:
    logger.exception(e)
    raise HTTPException(status_code=500, detail=str(e))
  
@router.post("/humancomplaint")
async def document_human_complaint(human_complaints: List[DocumentHumanResponseModel]) -> None:
  """
  This is the case that when the agent is trusted and confident with the classification, but the end user (SSG team)
  decided that the classification is wrong.
  """
  try:
    # TODO: Take agent out and start the workflow (Learning workflow), increase miss count of type and miss count of keywords
    for human_complaint in human_complaints:
      pass
      #await resume_conversation(human_complaint.document_name, human_complaint)
  except Exception as e:
    logger.exception(e)
    raise HTTPException(status_code=500, detail=str(e))

@router.get("/types")
async def get_classification_types() -> list[str]:
  """
  Get all classification types.
  """
  try:
    return await get_all_classification_types()
  except Exception as e:
    logger.exception(e)
    raise HTTPException(status_code=500, detail=str(e))

@router.get("/keywords/{classification_type}")
async def get_classification_keywords(classification_type: str) -> list[str]:
  """
  Get all classification keywords for a given classification type.
  """
  try:
    return await get_classification_keywords_by_type(classification_type)
  except Exception as e:
    logger.exception(e)
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
    logger.exception(e)
    raise HTTPException(status_code=500, detail=str(e))

@router.post("/keywords/deactivate")
async def deactivate_keywords() -> JSONResponse:
  """Deactivate keywords based on LastSeenDate, if the keyword has not been seen in the last 2 months."""
  try:
    await deactivate_stale_classification_keywords()
    return JSONResponse(status_code=200, content={"message": "Unused Keywords deactivated successfully"})
  except Exception as e:
    logger.exception(e)
    raise HTTPException(status_code=500, detail=str(e))