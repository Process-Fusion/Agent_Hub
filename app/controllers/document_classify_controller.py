# HTTP routes — health and tool API (Twilio/ElevenLabs call these from their dashboards)
import logging
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)
from src.models.document_classify_request_model import DocumentClassifyRequest
from src.models.document_classify_response_model import DocumentClassifyResponse
from src.models.add_classification_type_request_model import AddClassificationTypeRequest
from src.models.document_human_response_model import DocumentHumanResponseModel
from typing import List
from langgraph.errors import GraphInterrupt
from src.utils.pdf_utils import base64_pdf_to_base64_images

from src.services.postgres_db_service import get_all_classification_types, get_classification_keywords_by_type, add_classification_type, deactivate_stale_classification_keywords

router = APIRouter(prefix="/api/document-classify", tags=["document-classify"])

@router.post("/classify")
async def document_classify(request: Request, body: DocumentClassifyRequest) -> JSONResponse:
  """
  Classify a document into a classification type.
  """
  try:
    agent = request.app.state.agents["document_classify_agent"]
    images = base64_pdf_to_base64_images(body.File.File_content)
    agent_response = await agent.arun(body.document_name, images)
    return JSONResponse(
      status_code=200,
      content= DocumentClassifyResponse(
        document_name=body.document_name,
        classification_type= agent_response["classification_type"],
        confidence_score=agent_response["confidence_score"],
        reasoning=agent_response["reasoning"],
        matched_keyword_ids=agent_response.get("matched_keyword_ids", [])
      ).model_dump()
    )
  except GraphInterrupt as gi:
    interrupt_payload = gi.args[0] if gi.args else {}
    return JSONResponse(status_code=202, content={
        "status": "awaiting_human",
        "interrupt": interrupt_payload
    })
  except Exception as e:
    logger.exception(e)
    raise HTTPException(status_code=500, detail=str(e))

@router.post("/humanresponse")
async def document_human_response(request: Request, human_responses: List[DocumentHumanResponseModel]) -> JSONResponse:
  """
  Resume the conversation to finish agent workflow that executed during /classify api call.
  The conversation session is stored in postgres db, and is stored with the same name as document name.
  """
  try:
    agent = request.app.state.agents["document_classify_agent"]
    for human_response in human_responses:
      await agent.aresume(human_response.document_name, human_response)
    return JSONResponse(status_code=200, content={"status": "success"})
  except Exception as e:
    logger.exception(e)
    raise HTTPException(status_code=500, detail=str(e))
  
@router.post("/humancomplaint")
async def document_human_complaint(request: Request, human_complaints: List[DocumentHumanResponseModel]) -> None:
  """
  This is the case that when the agent is trusted and confident with the classification, but the end user (SSG team)
  decided that the classification is wrong.
  """
  try:
    agent = request.app.state.agents["document_classify_agent"]
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