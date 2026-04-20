from contextlib import asynccontextmanager
from typing import AsyncGenerator, Any
from src.core.env_config import EnvConfig
import asyncpg

_pool: asyncpg.Pool | None = None

async def init_pool() -> asyncpg.Pool:
  global _pool
  if _pool is None:
    configs = EnvConfig()
    _pool = await asyncpg.create_pool(
      dsn=configs.postgres_connection_string,
      min_size=1,
      max_size=10,
      command_timeout=60
    )
  return _pool

async def close_pool() -> None:
  global _pool
  if _pool is not None:
    await _pool.close()
    _pool = None

def get_pool() -> asyncpg.Pool:
  if _pool is None:
    raise RuntimeError("Database pool not initialized")
  return _pool

@asynccontextmanager
async def get_connection() -> AsyncGenerator[asyncpg.Connection, None]:
  pool = get_pool()
  async with pool.acquire() as connection:
    yield connection

def _placeholders(*args: Any) -> str:
  return ", ".join(f"${i + 1}" for i in range(len(args)))

async def select_query(query: str, *args: Any) -> list[dict[str, Any]]:
  """Execute a raw SELECT query and return rows as dicts."""
  async with get_connection() as connection:
    rows = await connection.fetch(query, *args)
    return [dict(row) for row in rows]

async def call_procedure(procedure: str, *args: Any) -> None:
  """Call a stored procedure by name, or execute a raw SQL statement."""
  if " " in procedure:
    query = procedure  # raw SQL (e.g. UPDATE ...)
  else:
    query = f"CALL {procedure}({_placeholders(*args)})"
  async with get_connection() as connection:
    await connection.execute(query, *args)

async def call_function_scalar(function: str, *args: Any) -> Any:
  """Call a scalar PostgreSQL function and return the single value."""
  query = f"SELECT {function}({_placeholders(*args)})"
  async with get_connection() as connection:
    return await connection.fetchval(query, *args)

async def call_function_record(function: str, *args: Any) -> list[dict[str, Any]]:
  """Call a set-returning PostgreSQL function and return rows as dicts."""
  query = f"SELECT * FROM {function}({_placeholders(*args)})"
  async with get_connection() as connection:
    rows = await connection.fetch(query, *args)
    return [dict(row) for row in rows]
