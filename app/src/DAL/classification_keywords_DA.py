"""
Data Access Layer for ClassificationKeywords table
Simple keyword management without stages
"""

from typing import List, Dict, Any, Optional
from src.models.classification_keyword_model import ClassificationKeywordModel
from src.enums.keyword_source_enum import KeywordSourceEnum
from src.enums.keyword_type_enum import KeywordTypeEnum
from src.infrastructure.postgres_db import call_procedure, call_function_record, select_query


async def _get_type_id(type_name: str) -> Optional[int]:
    """Get TypeID from TypeName. Returns None if not found."""
    query = "SELECT TypeID FROM ClassificationTypes WHERE TypeName = $1 AND IsActive = true"
    result = await select_query(query, type_name)
    return result[0]["typeid"] if result else None


async def _ensure_type_exists(type_name: str) -> int:
    """Get or create TypeID for a type name."""
    type_id = await _get_type_id(type_name)
    if type_id:
        return type_id

    query = """
        INSERT INTO ClassificationTypes (TypeName, IsActive)
        VALUES ($1, true)
        RETURNING TypeID
    """
    result = await select_query(query, type_name)
    return result[0]["typeid"] if result else 0


async def get_all_keywords() -> Dict[str, List[ClassificationKeywordModel]]:
    """
    Get all active keywords grouped by classification type.

    Returns:
        Dictionary: {type_name: [ClassificationKeywordModel, ...]}
        Example: {"Invoice": [ClassificationKeywordModel(...), ...]}
    """
    rows = await call_function_record("get_all_keywords")
    result: Dict[str, List[ClassificationKeywordModel]] = {}
    for row in rows:
        type_name = row["typename"]
        model = ClassificationKeywordModel(**{k: v for k, v in row.items() if k != "typename"})
        result.setdefault(type_name, []).append(model)
    return result

async def get_keywords_by_type(type_name: str) -> List[ClassificationKeywordModel]:
    """
    Get all active keywords for a specific classification type.

    Args:
        type_name: Classification type name (e.g., "Invoice")

    Returns:
        List of ClassificationKeywordModel for that type.
    """
    rows = await call_function_record("get_keywords_by_type", type_name)
    return [ClassificationKeywordModel(**row) for row in rows]

async def get_k_keywords_by_type(type_name: str, k: int = 100) -> List[ClassificationKeywordModel]:
    """
    Get the top-K active keywords for a classification type, ranked by
    signal strength (KeywordHitCount - KeywordMissCount DESC).

    Used for selective keyword loading in the system prompt — avoids
    dumping the entire keyword table into context as the agent learns.

    Args:
        type_name: Classification type name (e.g., "Invoice")
        k: Maximum number of keywords to return (default 100)

    Returns:
        List of ClassificationKeywordModel, best-performing first.
    """
    rows = await call_function_record("get_k_keywords_by_type", type_name, k)
    return [ClassificationKeywordModel(**row) for row in rows]


async def insert_keywords(type_name: str, keywords: list[ClassificationKeywordModel]) -> None:
    """
    Insert a new keyword for a classification type.
    Creates the type if it doesn't exist.
    
    Args:
        type_name: Classification type name (e.g., "Invoice")
        keyword: The keyword to add
    
    Returns:
        New KeywordID
    """
    type_id = await _ensure_type_exists(type_name)
    for keyword in keywords:
        # Converting string KeywordType to the enum value
        keyword_type_enum = KeywordTypeEnum[keyword.KeywordType]
        # Converting string Source to the enum value
        source_enum = KeywordSourceEnum[keyword.Source]
        await call_procedure("insert_classification_keyword", type_id, keyword.ClassificationKeyword, keyword_type_enum, source_enum)


async def remove_keyword(keyword_id: int) -> None:
    """
    Soft delete (deactivate) a keyword by ID.
    
    Args:
        keyword_id: The KeywordID to remove
    
    Returns:
        Number of rows updated (0 or 1)
    """
    await call_procedure("delete_classification_keyword_by_id", keyword_id)


async def remove_keyword_by_value(type_name: str, keyword: str) -> None:
    """
    Soft delete all keywords matching a specific value for a type.
    
    Args:
        type_name: Classification type name
        keyword: The keyword text to remove
    
    Returns:
        Number of rows updated
    """
    await call_procedure("delete_classification_keyword_by_value", type_name, keyword)

async def update_keyword_hit(keyword_id: int) -> None:
    """
    Increment HitCount and update LastSeenDate for a keyword.
    Call after a keyword contributed to a correct classification.

    Args:
        keyword_id: The KeywordID to update.
    """
    await call_procedure("update_keyword_hit", keyword_id)


async def update_keyword_miss(keyword_id: int) -> None:
    """
    Increment MissCount and update LastSeenDate for a keyword.
    Call after a keyword contributed to a wrong classification.

    Args:
        keyword_id: The KeywordID to update.
    """
    await call_procedure("update_keyword_miss", keyword_id)


async def deactivate_stale_keywords() -> int:
    """
    Soft-deactivate keywords whose LastSeenDate is older than 2 months.
    Skips SEED keywords that have never been seen (LastSeenDate IS NULL).
    Intended to be called weekly by an Azure scheduler via the API.

    Returns:
        Number of keywords deactivated.
    """
    rows = await call_function_record("deactivate_stale_keywords")
    return rows[0]["deactivate_stale_keywords"] if rows else 0

