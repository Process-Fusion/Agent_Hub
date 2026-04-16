"""
Pytest configuration: sys.path setup, environment variables, and module-level
workarounds so that test files can import the app's source modules cleanly.
"""

import importlib.util
import os
import sys
import types

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

# ---------------------------------------------------------------------------
# 3. Workaround for the oddly-named file "document_classify_response.model.py"
#
#    The controller imports:
#        from src.models.document_classify_response.model import DocumentClassifyResponse
#    Python's import system cannot resolve a dotted path whose intermediate
#    component ("document_classify_response") does not exist as a directory or
#    .py file — only "document_classify_response.model.py" exists.
#
#    We pre-populate sys.modules so that the import succeeds when the
#    controller module is loaded during test collection.
# ---------------------------------------------------------------------------
_models_dir = os.path.join(_app_dir, "src", "models")
_resp_file = os.path.join(_models_dir, "document_classify_response.model.py")

if "src.models.document_classify_response.model" not in sys.modules:
    # Ensure the intermediate "package" entry exists
    if "src.models.document_classify_response" not in sys.modules:
        _pkg = types.ModuleType("src.models.document_classify_response")
        _pkg.__path__ = []  # mark it as a package
        sys.modules["src.models.document_classify_response"] = _pkg

    _spec = importlib.util.spec_from_file_location(
        "src.models.document_classify_response.model", _resp_file
    )
    _mod = importlib.util.module_from_spec(_spec)
    sys.modules["src.models.document_classify_response.model"] = _mod
    _spec.loader.exec_module(_mod)
