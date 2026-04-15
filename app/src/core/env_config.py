import os
import dotenv
dotenv.load_dotenv()

class EnvConfig:
  def __init__(self):
    self.postgres_connection_string = os.getenv("POSTGRES_CONNECTION_STRING")