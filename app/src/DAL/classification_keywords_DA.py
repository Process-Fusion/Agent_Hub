"""
Data Access Layer for ClassificationKeywords table
Simple keyword management without stages
"""

from typing import List, Dict, Any, Optional
from src.core.db_connection import execute_query


def _get_type_id(type_name: str) -> Optional[int]:
    """Get TypeID from TypeName. Returns None if not found."""
    query = "SELECT TypeID FROM ClassificationTypes WHERE TypeName = :name AND IsActive = true"
    result = execute_query(query, {"name": type_name})
    return result[0]["typeid"] if result else None


def _ensure_type_exists(type_name: str) -> int:
    """Get or create TypeID for a type name."""
    type_id = _get_type_id(type_name)
    if type_id:
        return type_id
    
    query = """
        INSERT INTO ClassificationTypes (TypeName, IsActive)
        VALUES (:name, true)
        RETURNING TypeID
    """
    result = execute_query(query, {"name": type_name})
    return result[0]["typeid"] if result else 0


def get_all_keywords() -> Dict[str, List[str]]:
    """
    Get all active keywords grouped by classification type.
    
    Returns:
        Dictionary: {type_name: [keyword1, keyword2, ...]}
        Example: {"Invoice": ["invoice", "balance", "payment"], "Purchase Order": ["PO", "order"]}
    """
    query = """
        SELECT 
            t.TypeName AS ClassificationType,
            k.ClassificationKeywords
        FROM ClassificationKeywords k
        JOIN ClassificationTypes t ON k.TypeID = t.TypeID
        WHERE k.IsActive = true AND t.IsActive = true
        ORDER BY t.TypeName, k.KeywordID
    """
    result = execute_query(query)
    
    keywords_by_type: Dict[str, List[str]] = {}
    for row in result:
        type_name = row["classificationtype"]
        keyword = row["classificationkeywords"]
        if type_name not in keywords_by_type:
            keywords_by_type[type_name] = []
        keywords_by_type[type_name].append(keyword)
    
    return keywords_by_type


def get_keywords_by_type(type_name: str) -> List[str]:
    """
    Get all active keywords for a specific classification type.
    
    Args:
        type_name: Classification type name (e.g., "Invoice")
    
    Returns:
        List of keywords for that type
    """
    query = """
        SELECT k.ClassificationKeywords
        FROM ClassificationKeywords k
        JOIN ClassificationTypes t ON k.TypeID = t.TypeID
        WHERE t.TypeName = :type AND k.IsActive = true AND t.IsActive = true
        ORDER BY k.KeywordID
    """
    result = execute_query(query, {"type": type_name})
    return [row["classificationkeywords"] for row in result]


def insert_keyword(type_name: str, keyword: str) -> int:
    """
    Insert a new keyword for a classification type.
    Creates the type if it doesn't exist.
    
    Args:
        type_name: Classification type name (e.g., "Invoice")
        keyword: The keyword to add
    
    Returns:
        New KeywordID
    """
    type_id = _ensure_type_exists(type_name)
    
    query = """
        INSERT INTO ClassificationKeywords (TypeID, ClassificationKeywords, IsActive)
        VALUES (:type_id, :keyword, true)
        RETURNING KeywordID
    """
    result = execute_query(query, {
        "type_id": type_id,
        "keyword": keyword
    })
    return result[0]["keywordid"] if result else 0


def insert_keywords(type_name: str, keywords: List[str]) -> List[int]:
    """
    Insert multiple keywords for a classification type.
    
    Args:
        type_name: Classification type name
        keywords: List of keywords to add
    
    Returns:
        List of new KeywordIDs
    """
    type_id = _ensure_type_exists(type_name)
    inserted_ids = []
    
    for keyword in keywords:
        query = """
            INSERT INTO ClassificationKeywords (TypeID, ClassificationKeywords, IsActive)
            VALUES (:type_id, :keyword, true)
            RETURNING KeywordID
        """
        result = execute_query(query, {
            "type_id": type_id,
            "keyword": keyword
        })
        if result:
            inserted_ids.append(result[0]["keywordid"])
    
    return inserted_ids


def remove_keyword(keyword_id: int) -> int:
    """
    Soft delete (deactivate) a keyword by ID.
    
    Args:
        keyword_id: The KeywordID to remove
    
    Returns:
        Number of rows updated (0 or 1)
    """
    query = """
        UPDATE ClassificationKeywords
        SET IsActive = false
        WHERE KeywordID = :id
    """
    return execute_query(query, {"id": keyword_id}, fetch=False)


def remove_keyword_by_value(type_name: str, keyword: str) -> int:
    """
    Soft delete all keywords matching a specific value for a type.
    
    Args:
        type_name: Classification type name
        keyword: The keyword text to remove
    
    Returns:
        Number of rows updated
    """
    query = """
        UPDATE ClassificationKeywords
        SET IsActive = false
        WHERE TypeID = (SELECT TypeID FROM ClassificationTypes WHERE TypeName = :type)
          AND ClassificationKeywords = :keyword
    """
    return execute_query(query, {"type": type_name, "keyword": keyword}, fetch=False)


def hard_delete_keyword(keyword_id: int) -> int:
    """
    Permanently delete a keyword by ID.
    
    Args:
        keyword_id: The KeywordID to delete
    
    Returns:
        Number of rows deleted
    """
    query = "DELETE FROM ClassificationKeywords WHERE KeywordID = :id"
    return execute_query(query, {"id": keyword_id}, fetch=False)
