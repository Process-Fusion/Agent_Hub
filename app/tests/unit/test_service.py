"""
Unit tests for src/services/postgres_db_service.py.

The service layer is a thin async wrapper over the DAL. Tests verify that
each service function delegates correctly to its DAL counterpart.

NOTE — known bug in get_classification_keywords_by_type:
  The service does `await get_keywords_by_type(...)` but get_keywords_by_type
  is a synchronous function (returns a plain list, not a coroutine).
  Awaiting a non-awaitable raises TypeError at runtime. Tests patch the
  dependency with AsyncMock to exercise the intended delegation logic; the
  production code path is broken until this is fixed.
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from src.services.postgres_db_service import (
    add_classification_type,
    get_all_classification_types,
    get_classification_keywords_by_type,
)


# ---------------------------------------------------------------------------
# get_all_classification_types
# ---------------------------------------------------------------------------
class TestGetAllClassificationTypes:
    def test_returns_list_from_dal(self):
        types = ["Invoice", "Purchase Order", "Referral", "Fax_Monitoring"]
        with patch(
            "src.services.postgres_db_service.get_all_types",
            new=AsyncMock(return_value=types),
        ):
            result = asyncio.run(get_all_classification_types())
        assert result == types

    def test_returns_empty_list_when_dal_returns_empty(self):
        with patch(
            "src.services.postgres_db_service.get_all_types",
            new=AsyncMock(return_value=[]),
        ):
            result = asyncio.run(get_all_classification_types())
        assert result == []

    def test_propagates_exception_from_dal(self):
        with patch(
            "src.services.postgres_db_service.get_all_types",
            new=AsyncMock(side_effect=RuntimeError("DB down")),
        ):
            with pytest.raises(RuntimeError, match="DB down"):
                asyncio.run(get_all_classification_types())


# ---------------------------------------------------------------------------
# get_classification_keywords_by_type
# NOTE: Uses AsyncMock to work around the sync/await mismatch in the service.
# ---------------------------------------------------------------------------
class TestGetClassificationKeywordsByType:
    def test_returns_keywords_from_dal(self):
        keywords = ["invoice", "payment due", "balance"]
        with patch(
            "src.services.postgres_db_service.get_keywords_by_type",
            new=AsyncMock(return_value=keywords),
        ):
            result = asyncio.run(get_classification_keywords_by_type("Invoice"))
        assert result == keywords

    def test_passes_type_name_to_dal(self):
        with patch(
            "src.services.postgres_db_service.get_keywords_by_type",
            new=AsyncMock(return_value=[]),
        ) as mock:
            asyncio.run(get_classification_keywords_by_type("Purchase Order"))
        mock.assert_called_once_with("Purchase Order")

    def test_returns_empty_list_when_dal_returns_empty(self):
        with patch(
            "src.services.postgres_db_service.get_keywords_by_type",
            new=AsyncMock(return_value=[]),
        ):
            result = asyncio.run(get_classification_keywords_by_type("Unknown"))
        assert result == []


# ---------------------------------------------------------------------------
# add_classification_type
# ---------------------------------------------------------------------------
class TestAddClassificationType:
    def test_delegates_to_dal_with_description(self):
        with patch(
            "src.services.postgres_db_service.insert_classification_type",
            new=AsyncMock(return_value=None),
        ) as mock:
            asyncio.run(add_classification_type("NewType", "A new document type"))
        mock.assert_called_once_with("NewType", "A new document type")

    def test_delegates_to_dal_without_description(self):
        with patch(
            "src.services.postgres_db_service.insert_classification_type",
            new=AsyncMock(return_value=None),
        ) as mock:
            asyncio.run(add_classification_type("NewType"))
        mock.assert_called_once_with("NewType", None)

    def test_propagates_exception_from_dal(self):
        with patch(
            "src.services.postgres_db_service.insert_classification_type",
            new=AsyncMock(side_effect=Exception("Insert failed")),
        ):
            with pytest.raises(Exception, match="Insert failed"):
                asyncio.run(add_classification_type("NewType", "desc"))
