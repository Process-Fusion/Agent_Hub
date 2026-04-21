from langchain_core.tools import InjectedToolCallId, tool
from typing import Annotated, Literal, List
from pathlib import Path
from datetime import date, datetime
from langchain_core.messages import ToolMessage
from langgraph.types import Command, interrupt
from src.services.postgres_db_service import get_all_classification_types, insert_keywords, delete_classification_keywords
import csv
import json
from src.models.classification_keyword_model import ClassificationKeywordModel

# @tool
# def create_classification_reasoning(
#     document_name: str,
#     classification_type: str,
#     confidence_score: float,
#     reasoning: str,
#     tool_call_id: Annotated[str, InjectedToolCallId],
# ):
#     """Create a classification reasoning markdown file for the document.

#     This tool saves the classification details to a timestamped markdown file
#     in the agent_classification_reasoning directory for record keeping and analysis.

#     Args:
#         document_name: The name of the document.
#         classification_type: The type of classification (Invoice, Purchase Order, Referral, etc.).
#         confidence_score: The confidence score of the classification (0-100).
#         reasoning: The detailed reasoning for the classification.
#     """

#     return Command(
#         update={
#             "messages": [ToolMessage(content=f"Classification reasoning saved to {filename}", tool_call_id=tool_call_id)],
#             "classification_type": classification_type,
#             "confidence_score": confidence_score / 100.0,
#             "document_name": document_name,
#             "reasoning": reasoning
#         }
#     )


@tool
def request_human_confirmation(
    classification_type: str,
    confidence_score: float,
    reasoning: str,
    tool_call_id: Annotated[str, InjectedToolCallId]
):
    """Request human confirmation for a classification.
    
    Use this tool when confidence is low or the classification type is not trusted yet.
    This will pause execution and wait for human approval.
    
    Args:
        classification_type: The proposed classification type.
        confidence_score: The confidence score (0-100).
        reasoning: Explanation for why this classification was chosen.
    """
    # This tool sets up the state for human confirmation
    # The actual interrupt happens in the human_confirmation_node
    return Command(
        update={
            "messages": [ToolMessage(
                content=f"Classification '{classification_type}' ({confidence_score}%) requires human confirmation.",
                tool_call_id=tool_call_id
            )],
            "classification_type": classification_type,
            "confidence_score": confidence_score
        },
        goto="human_confirmation"
    )

@tool
async def classify_document(
    classification_type: str, 
    confidence_score: float,
    matched_keyword_ids: List[int],
    reasoning: str, 
    tool_call_id: Annotated[str, InjectedToolCallId]
    ):
    """Classify a document into a classification type.
    
    Use this tool to classify a document into a classification type.
    
    Args:
        classification_type: The classification type to classify the document into.
        confidence_score: The confidence score of the classification (0-1.0).
        matched_keyword_ids: The IDs of the keywords that matched the document.
        reasoning: The detailed reasoning for the classification.
    """
    # Check for classification type is valid
    # print(f"Classification Types: {await get_all_classification_types()}")
    valid_types = await get_all_classification_types()
    if confidence_score > 1.0:
        return Command(
            update={
                "messages": [ToolMessage(content=f"Error: Confidence score must be between 0 and 1.0", tool_call_id=tool_call_id)],
            }
        )
    if classification_type not in valid_types:
        return Command(
            update={
                "messages": [ToolMessage(content=f"Error: '{classification_type}' is not a valid classification type. Valid types: {valid_types}", tool_call_id=tool_call_id)],
            }
        )
    
    return Command(
        update={
            "messages": [ToolMessage(content=f"Document classified as '{classification_type}' ({confidence_score}%) with reasoning: {reasoning}", tool_call_id=tool_call_id)],
            "classification_type": classification_type,
            "confidence_score": confidence_score,
            "reasoning": reasoning,
            "keyword_ids": matched_keyword_ids
        }
    )

@tool
async def save_extracted_keywords(
    classification_type: str,
    keywords: list[ClassificationKeywordModel],
    tool_call_id: Annotated[str, InjectedToolCallId]
):
    """Save AI-extracted keywords for a classification type.
    
    Use this tool after analyzing a document to store discovered keywords
    that help distinguish this document type. The AI determines these keywords
    based on visual and text analysis of the document.
    
    Args:
        classification_type: The classification type the keywords belong to.
        keywords: List of keywords extracted by AI analysis (e.g., ["PO #", "Purchase Order", "Vendor ID"])
    """
    # Validate that the classification type exists
    valid_types = await get_all_classification_types()
    if classification_type not in valid_types:
        return Command(
            update={
                "messages": [ToolMessage(
                    content=f"Error: '{classification_type}' is not a valid classification type. Valid types: {valid_types}",
                    tool_call_id=tool_call_id
                )],
            }
        )
    
    if len(keywords) == 0:
        return Command(
            update={
                "messages": [ToolMessage(
                    content=f"No valid keywords provided for '{classification_type}'",
                    tool_call_id=tool_call_id
                )],
            }
        )
    
    try:
        # Insert keywords into database
        await insert_keywords(classification_type, keywords)
        
        return Command(
            update={
                "messages": [ToolMessage(
                    content=f"AI extracted {len(keywords)} keywords for '{classification_type}': {', '.join(keywords)}",
                    tool_call_id=tool_call_id
                )],
                "extracted_keywords": keywords,
                "keyword_ids": []
            }
        )
    except Exception as e:
        return Command(
            update={
                "messages": [ToolMessage(
                    content=f"Error saving keywords for '{classification_type}': {e}",
                    tool_call_id=tool_call_id
                )],
            }
        )

@tool
async def remove_keywords(keywords: list[str], classification_type: str, tool_call_id: Annotated[str, InjectedToolCallId]):
    """Remove keywords from a classification type.
    
    Use this tool to remove keywords from a classification type.
    
    Args:
        keywords: The keywords to remove.
        classification_type: The classification type to remove the keywords from.
    """
    # Validate that the classification type exists
    valid_types = await get_all_classification_types()
    if classification_type not in valid_types:
        return Command(
            update={
                "messages": [ToolMessage(content=f"Error: '{classification_type}' is not a valid classification type. Valid types: {valid_types}", tool_call_id=tool_call_id)],
            }
        )
    # Validate that the keywords are not empty
    if not keywords:
        return Command(
            update={
                "messages": [ToolMessage(content="No keywords provided", tool_call_id=tool_call_id)],
            }
        )
    try:
        # Remove keywords from database
        removed_ids = delete_classification_keywords(classification_type, keywords)
    except Exception as e:
        return Command(
            update={
                "messages": [ToolMessage(content=f"Error removing keywords for '{classification_type}': {e}", tool_call_id=tool_call_id)],
            }
        )

tool_list = [request_human_confirmation, classify_document, remove_keywords]
