from src.infrastructure.postgres_db import get_connection, call_function_record
from src.DAL.classification_keywords_DA import get_keywords_by_type
from src.DAL.classification_types_DA import get_all_types, insert_classification_type

from typing import Any

async def get_all_classification_types() -> list[str]:
  return await get_all_types()

async def get_classification_keywords_by_type(classification_type: str) -> list[str]:
  return await get_keywords_by_type(classification_type) 

async def add_classification_type(classification_type: str, description: str = None) -> None:
  return await insert_classification_type(classification_type, description)