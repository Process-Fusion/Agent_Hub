"""
Data Access Layer for ClassificationTypeTrustSystem table
Manages HitCount and MissCount for trust-based classification
"""

from typing import Dict, Any, Optional
from src.core.db_connection import execute_query


def get_trust_by_type(type_name: str) -> Optional[Dict[str, Any]]:
    """
    Get trust record for a classification type.
    
    Returns:
        Dict with TrustID, TypeName, HitCount, MissCount or None
    """
    query = """
        SELECT 
            ts.TrustID,
            ct.TypeName AS ClassificationType,
            ts.HitCount,
            ts.MissCount,
            ts.CreatedDate,
            ts.ModifiedDate
        FROM ClassificationTypeTrustSystem ts
        JOIN ClassificationTypes ct ON ts.TypeID = ct.TypeID
        WHERE ct.TypeName = :type
    """
    result = execute_query(query, {"type": type_name})
    return result[0] if result else None


def get_all_trust() -> Dict[str, Dict[str, int]]:
    """
    Get all trust records organized by type name.
    
    Returns:
        Dict: {type_name: {"HitCount": x, "MissCount": y}}
    """
    query = """
        SELECT 
            ct.TypeName AS ClassificationType,
            ts.HitCount,
            ts.MissCount
        FROM ClassificationTypeTrustSystem ts
        JOIN ClassificationTypes ct ON ts.TypeID = ct.TypeID
        ORDER BY ct.TypeName
    """
    result = execute_query(query)
    
    return {
        row["classificationtype"]: {
            "HitCount": row["hitcount"],
            "MissCount": row["misscount"]
        }
        for row in result
    }


def update_hit_count(type_name: str, hit_count: int) -> int:
    """
    Set HitCount to a specific value.
    
    Args:
        type_name: Classification type name
        hit_count: New HitCount value
    
    Returns:
        Number of rows updated
    """
    query = """
        UPDATE ClassificationTypeTrustSystem
        SET HitCount = :hits
        WHERE TypeID = (SELECT TypeID FROM ClassificationTypes WHERE TypeName = :type)
    """
    return execute_query(query, {"hits": hit_count, "type": type_name}, fetch=False)


def increment_hit_count(type_name: str) -> int:
    """
    Increment HitCount by 1.
    
    Returns:
        Number of rows updated
    """
    query = """
        UPDATE ClassificationTypeTrustSystem
        SET HitCount = HitCount + 1
        WHERE TypeID = (SELECT TypeID FROM ClassificationTypes WHERE TypeName = :type)
    """
    return execute_query(query, {"type": type_name}, fetch=False)


def update_miss_count(type_name: str, miss_count: int) -> int:
    """
    Set MissCount to a specific value.
    
    Args:
        type_name: Classification type name
        miss_count: New MissCount value
    
    Returns:
        Number of rows updated
    """
    query = """
        UPDATE ClassificationTypeTrustSystem
        SET MissCount = :misses
        WHERE TypeID = (SELECT TypeID FROM ClassificationTypes WHERE TypeName = :type)
    """
    return execute_query(query, {"misses": miss_count, "type": type_name}, fetch=False)


def increment_miss_count(type_name: str) -> int:
    """
    Increment MissCount by 1.
    
    Returns:
        Number of rows updated
    """
    query = """
        UPDATE ClassificationTypeTrustSystem
        SET MissCount = MissCount + 1
        WHERE TypeID = (SELECT TypeID FROM ClassificationTypes WHERE TypeName = :type)
    """
    return execute_query(query, {"type": type_name}, fetch=False)


def is_trusted(type_name: str, min_hits: int = 3) -> bool:
    """
    Check if a type is trusted (HitCount - MissCount >= min_hits).
    
    Trust is earned when net successful classifications (hits minus misses)
    meets the minimum threshold. Misses reduce the trust score.
    
    Args:
        type_name: Classification type name
        min_hits: Minimum net hits required (default 3)
    
    Returns:
        True if trusted, False otherwise
    """
    query = """
        SELECT ts.HitCount, ts.MissCount
        FROM ClassificationTypeTrustSystem ts
        JOIN ClassificationTypes ct ON ts.TypeID = ct.TypeID
        WHERE ct.TypeName = :type
    """
    result = execute_query(query, {"type": type_name})
    
    if not result:
        return False
    
    row = result[0]
    net_hits = row["hitcount"] - row["misscount"]
    return net_hits >= min_hits


def reset_trust(type_name: str) -> int:
    """
    Reset HitCount and MissCount to 0.
    
    Returns:
        Number of rows updated
    """
    query = """
        UPDATE ClassificationTypeTrustSystem
        SET HitCount = 0, MissCount = 0
        WHERE TypeID = (SELECT TypeID FROM ClassificationTypes WHERE TypeName = :type)
    """
    return execute_query(query, {"type": type_name}, fetch=False)
