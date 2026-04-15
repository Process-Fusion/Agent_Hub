from src.infrastructure.postgres_db import call_function_record, call_procedure

async def get_all_types() -> list[str]:
  """Get list of all active classification type names."""
  row_dicts = await call_function_record("get_classification_types")
  return [row_dict["TypeName"] for row_dict in row_dicts] if row_dicts else []

async def insert_classification_type(classification_type: str, description: str = None) -> None:
  """Add a new classification type."""
  await call_procedure("insert_classification_type", classification_type, description)
  
  