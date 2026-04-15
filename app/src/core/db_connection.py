"""
Simple PostgreSQL database connection module
"""

import os
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

# Database Configuration
DATABASE_URL = os.getenv("POSTGRES_CONNECTION_STRING")

# Create engine
engine = create_engine(DATABASE_URL, echo=False)


def execute_query(
    query: str,
    params: Optional[Dict[str, Any]] = None,
    fetch: bool = True
) -> List[Dict[str, Any]] | int:
    """
    Execute a SQL query with optional parameter binding.
    
    Args:
        query: SQL query string (use :param_name for parameters)
        params: Dictionary of parameters to bind
        fetch: If True returns rows, if False returns row count
    
    Returns:
        List of dictionaries (rows) or row count
    
    Usage:
        # SELECT
        rows = execute_query(
            "SELECT * FROM ClassificationKeywords WHERE ClassificationType = :type",
            {"type": "Invoice"}
        )
        
        # INSERT/UPDATE/DELETE
        count = execute_query(
            "UPDATE ClassificationTrust SET HitCount = HitCount + 1 WHERE ClassificationType = :type",
            {"type": "Invoice"},
            fetch=False
        )
    """
    with engine.connect() as conn:
        result = conn.execute(text(query), params or {})
        conn.commit()
        
        if fetch:
            rows = result.fetchall()
            columns = result.keys()
            return [dict(zip(columns, row)) for row in rows]
        else:
            return result.rowcount

if __name__ == "__main__":
    rows = execute_query("SELECT * FROM ClassificationKeywords")
    print(rows)