import os
import dotenv
dotenv.load_dotenv()

class EnvConfig:
  def __init__(self):
    dsn = os.getenv("POSTGRES_CONNECTION_STRING", "")
    self.postgres_connection_string = dsn.replace("postgresql+psycopg2://", "postgresql://").replace("postgresql+asyncpg://", "postgresql://")