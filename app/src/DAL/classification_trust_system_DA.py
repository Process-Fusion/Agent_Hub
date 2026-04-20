"""
Data Access Layer for ClassificationTypeTrustSystem table.
Manages HitCount and MissCount for trust-based classification.
"""

from typing import Dict, Optional
from src.infrastructure.postgres_db import call_procedure, select_query


async def get_trust_by_type(type_name: str) -> Optional[Dict]:
    """Get trust record for a classification type."""
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
        WHERE ct.TypeName = $1
    """
    result = await select_query(query, type_name)
    return result[0] if result else None


async def get_all_trust() -> Dict[str, Dict[str, int]]:
    """Get all trust records organised by type name."""
    query = """
        SELECT
            ct.TypeName AS ClassificationType,
            ts.HitCount,
            ts.MissCount
        FROM ClassificationTypeTrustSystem ts
        JOIN ClassificationTypes ct ON ts.TypeID = ct.TypeID
        ORDER BY ct.TypeName
    """
    result = await select_query(query)
    return {
        row["classificationtype"]: {
            "HitCount": row["hitcount"],
            "MissCount": row["misscount"],
        }
        for row in result
    }


async def update_hit_count(type_name: str, hit_count: int) -> None:
    """Set HitCount to a specific value."""
    query = """
        UPDATE ClassificationTypeTrustSystem
        SET HitCount = $1
        WHERE TypeID = (SELECT TypeID FROM ClassificationTypes WHERE TypeName = $2)
    """
    await call_procedure(query, hit_count, type_name)


async def increment_hit_count(type_name: str) -> None:
    """Increment HitCount by 1."""
    query = """
        UPDATE ClassificationTypeTrustSystem
        SET HitCount = HitCount + 1
        WHERE TypeID = (SELECT TypeID FROM ClassificationTypes WHERE TypeName = $1)
    """
    await call_procedure(query, type_name)


async def update_miss_count(type_name: str, miss_count: int) -> None:
    """Set MissCount to a specific value."""
    query = """
        UPDATE ClassificationTypeTrustSystem
        SET MissCount = $1
        WHERE TypeID = (SELECT TypeID FROM ClassificationTypes WHERE TypeName = $2)
    """
    await call_procedure(query, miss_count, type_name)


async def increment_miss_count(type_name: str) -> None:
    """Increment MissCount by 1."""
    query = """
        UPDATE ClassificationTypeTrustSystem
        SET MissCount = MissCount + 1
        WHERE TypeID = (SELECT TypeID FROM ClassificationTypes WHERE TypeName = $1)
    """
    await call_procedure(query, type_name)


async def is_trusted(type_name: str, min_hits: int = 3) -> bool:
    """Return True if (HitCount - MissCount) >= min_hits."""
    query = """
        SELECT ts.HitCount, ts.MissCount
        FROM ClassificationTypeTrustSystem ts
        JOIN ClassificationTypes ct ON ts.TypeID = ct.TypeID
        WHERE ct.TypeName = $1
    """
    result = await select_query(query, type_name)
    if not result:
        return False
    row = result[0]
    return (row["hitcount"] - row["misscount"]) >= min_hits


async def reset_trust(type_name: str) -> None:
    """Reset HitCount and MissCount to 0."""
    query = """
        UPDATE ClassificationTypeTrustSystem
        SET HitCount = 0, MissCount = 0
        WHERE TypeID = (SELECT TypeID FROM ClassificationTypes WHERE TypeName = $1)
    """
    await call_procedure(query, type_name)