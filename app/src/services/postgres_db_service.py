from src.infrastructure.postgres_db import get_connection, call_function_record
from src.DAL.classification_keywords_DA import (
  get_keywords_by_type, insert_keywords, 
  remove_keyword_by_value, 
  get_all_keywords, 
  get_k_keywords_by_type, 
  update_keyword_hit, 
  update_keyword_miss, 
  deactivate_stale_keywords
)
from src.DAL.classification_types_DA import get_all_types, insert_classification_type
from src.DAL.classification_trust_system_DA import get_trust_by_type, increment_hit_count, increment_miss_count, is_trusted
from src.models.classification_keyword_model import ClassificationKeywordModel

from typing import Any, Dict, List

async def get_all_classification_types() -> list[str]:
  return await get_all_types()

async def add_classification_type(classification_type: str, description: str = None) -> None:
  return await insert_classification_type(classification_type, description)

# ----------------------------
# Classification Keywords
# ----------------------------
async def get_classification_keywords_by_type(classification_type: str) -> list[ClassificationKeywordModel]:
  return await get_keywords_by_type(classification_type) 

async def get_all_classification_keywords() -> Dict[str, List[ClassificationKeywordModel]]:
  return await get_all_keywords()

async def get_k_classification_keywords_by_type(classification_type: str, k: int) -> list[ClassificationKeywordModel]:
  return await get_k_keywords_by_type(classification_type, k)

async def insert_classification_keywords(classification_type: str, keywords: list[ClassificationKeywordModel]) -> None:
  return await insert_keywords(classification_type, keywords)

async def delete_classification_keywords(classification_type: str, keywords: list[str]) -> None:
  for keyword in keywords:
    await remove_keyword_by_value(classification_type, keyword)

async def update_classification_keyword_hit(keyword_id: int) -> None:
  return await update_keyword_hit(keyword_id)

async def update_classification_keywords_hit(keyword_ids: list[int]) -> None:
  for keyword_id in keyword_ids:
    await update_keyword_hit(keyword_id)

async def update_classification_keyword_miss(keyword_id: int) -> None:
  return await update_keyword_miss(keyword_id)

async def update_classification_keywords_miss(keyword_ids: list[int]) -> None:
  for keyword_id in keyword_ids:
    await update_keyword_miss(keyword_id)

async def deactivate_stale_classification_keywords() -> None:
  return await deactivate_stale_keywords()

# ----------------------------
# Trust System
# ----------------------------
async def update_hit_count(type_name: str) -> None:
  return await increment_hit_count(type_name)

async def update_miss_count(type_name: str) -> None:
  return await increment_miss_count(type_name)

async def is_type_trusted(type_name: str) -> bool:
  return await is_trusted(type_name)
  
async def get_trust_by_classification_type(type_name: str) -> float:
  return await get_trust_by_type(type_name)