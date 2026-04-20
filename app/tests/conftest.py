"""
Pytest configuration: sys.path setup and environment variables so that test
files can import the app's source modules cleanly.
"""

import os
import sys

# ---------------------------------------------------------------------------
# 1. Environment variables
#    db_connection.py calls create_engine() at import time, so the connection
#    string must be set BEFORE any app module is imported.
# ---------------------------------------------------------------------------
os.environ.setdefault(
    "POSTGRES_CONNECTION_STRING",
    "postgresql+psycopg2://test:test@localhost/testdb",
)

# ---------------------------------------------------------------------------
# 2. sys.path — add app/ so that "from src.x import y" and
#    "from controllers.x import y" resolve to the actual source files.
# ---------------------------------------------------------------------------
_app_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _app_dir not in sys.path:
    sys.path.insert(0, _app_dir)
