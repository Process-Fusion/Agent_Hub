from contextlib import asynccontextmanager
from typing import AsyncGenerator
from src.core.env_config import EnvConfig
import asyncpg
from typing import Any

# Singleton pattern design
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

async def select_query(query: str, *args: Any) -> list[dict[str, Any]]:
  """Execute a SELECT query and return the results."""
  async with get_connection() as connection:
    rows = await connection.fetch(query, *args)
    return [dict(row) for row in rows]

async def call_procedure(procedure: str, *args: Any) -> None:
  """Call a stored procedure and return no value."""
  async with get_connection() as connection:
    await connection.execute(procedure, *args)

async def call_function_scalar(function: str, *args: Any) -> Any:
  """Call a scalar function and return the result."""
  async with get_connection() as connection:
    return await connection.fetchval(function, *args)

async def call_function_record(function: str, *args: Any) -> dict[str, Any]:
  """Call a record function and return the result."""
  async with get_connection() as connection:
    rows = await connection.fetch(function, *args)
    return [dict(row) for row in rows]