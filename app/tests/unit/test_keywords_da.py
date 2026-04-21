"""
Unit tests for src/DAL/classification_keywords_DA.py.

Sync helpers (_get_type_id, _ensure_type_exists) mock execute_query.
Async functions mock call_function_record / call_procedure via asyncio.run().
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from src.DAL.classification_keywords_DA import (
    _ensure_type_exists,
    _get_type_id,
    deactivate_stale_keywords,
    get_all_keywords,
    get_k_keywords_by_type,
    get_keywords_by_type,
    insert_keywords,
    remove_keyword,
    remove_keyword_by_value,
    update_keyword_hit,
    update_keyword_miss,
)
from src.models.classification_keyword_model import ClassificationKeywordModel

_SQ = "src.DAL.classification_keywords_DA.select_query"
_CFR = "src.DAL.classification_keywords_DA.call_function_record"
_CP = "src.DAL.classification_keywords_DA.call_procedure"


def _kw(**overrides) -> ClassificationKeywordModel:
    """Build a minimal ClassificationKeywordModel using field names (populate_by_name=True)."""
    defaults = {"ClassificationKeyword": "invoice", "KeywordType": "PRIMARY", "Source": "SEED"}
    return ClassificationKeywordModel(**{**defaults, **overrides})


def _row(**overrides) -> dict:
    """Build a minimal keyword DB row matching asyncpg lowercase column names / model aliases."""
    base = {
        "keywordid": 1, "typeid": 1, "classificationkeywords": "invoice",
        "isactive": True, "keywordtype": "PRIMARY", "source": "SEED",
        "keywordhitcount": 0, "keywordmisscount": 0,
        "lastseendate": None, "createddate": None, "modifieddate": None,
    }
    return {**base, **overrides}


# ---------------------------------------------------------------------------
# _get_type_id  (async)
# ---------------------------------------------------------------------------
class TestGetTypeId:
    def test_returns_id_when_type_found(self):
        async def run():
            with patch(_SQ, new_callable=AsyncMock, return_value=[{"typeid": 42}]):
                return await _get_type_id("Invoice")
        assert asyncio.run(run()) == 42

    def test_returns_none_when_type_not_found(self):
        async def run():
            with patch(_SQ, new_callable=AsyncMock, return_value=[]):
                return await _get_type_id("Unknown")
        assert asyncio.run(run()) is None

    def test_passes_type_name_to_query(self):
        async def run():
            with patch(_SQ, new_callable=AsyncMock, return_value=[{"typeid": 1}]) as mock:
                await _get_type_id("Purchase Order")
                return mock
        mock = asyncio.run(run())
        assert "Purchase Order" in str(mock.call_args)


# ---------------------------------------------------------------------------
# _ensure_type_exists  (async)
# ---------------------------------------------------------------------------
class TestEnsureTypeExists:
    def test_returns_existing_type_id_without_inserting(self):
        async def run():
            with patch(_SQ, new_callable=AsyncMock, return_value=[{"typeid": 5}]) as mock:
                result = await _ensure_type_exists("Invoice")
                return result, mock
        result, mock = asyncio.run(run())
        assert result == 5
        mock.assert_called_once()

    def test_inserts_and_returns_new_id_when_type_missing(self):
        async def run():
            with patch(_SQ, new_callable=AsyncMock, side_effect=[[], [{"typeid": 99}]]) as mock:
                result = await _ensure_type_exists("NewType")
                return result, mock
        result, mock = asyncio.run(run())
        assert result == 99
        assert mock.call_count == 2

    def test_returns_zero_when_insert_returns_nothing(self):
        async def run():
            with patch(_SQ, new_callable=AsyncMock, side_effect=[[], []]):
                return await _ensure_type_exists("BadType")
        assert asyncio.run(run()) == 0


# ---------------------------------------------------------------------------
# get_all_keywords  (async)
# ---------------------------------------------------------------------------
class TestGetAllKeywords:
    def test_groups_keywords_by_type(self):
        rows = [
            {"typename": "Invoice", **_row(classificationkeywords="invoice")},
            {"typename": "Invoice", **_row(classificationkeywords="payment due")},
            {"typename": "Purchase Order", **_row(classificationkeywords="PO number")},
        ]
        async def run():
            with patch(_CFR, new_callable=AsyncMock, return_value=rows):
                return await get_all_keywords()
        result = asyncio.run(run())
        assert set(result.keys()) == {"Invoice", "Purchase Order"}
        assert len(result["Invoice"]) == 2
        assert len(result["Purchase Order"]) == 1

    def test_returns_classification_keyword_models(self):
        async def run():
            with patch(_CFR, new_callable=AsyncMock, return_value=[{"typename": "Invoice", **_row()}]):
                return await get_all_keywords()
        result = asyncio.run(run())
        assert isinstance(result["Invoice"][0], ClassificationKeywordModel)

    def test_returns_empty_dict_when_no_rows(self):
        async def run():
            with patch(_CFR, new_callable=AsyncMock, return_value=[]):
                return await get_all_keywords()
        assert asyncio.run(run()) == {}

    def test_preserves_insertion_order_within_type(self):
        rows = [
            {"typename": "Invoice", **_row(classificationkeywords="first")},
            {"typename": "Invoice", **_row(classificationkeywords="second")},
            {"typename": "Invoice", **_row(classificationkeywords="third")},
        ]
        async def run():
            with patch(_CFR, new_callable=AsyncMock, return_value=rows):
                return await get_all_keywords()
        result = asyncio.run(run())
        assert [m.ClassificationKeyword for m in result["Invoice"]] == ["first", "second", "third"]


# ---------------------------------------------------------------------------
# get_keywords_by_type  (async)
# ---------------------------------------------------------------------------
class TestGetKeywordsByType:
    def test_returns_list_of_models(self):
        rows = [_row(classificationkeywords="invoice"), _row(classificationkeywords="balance due")]
        async def run():
            with patch(_CFR, new_callable=AsyncMock, return_value=rows):
                return await get_keywords_by_type("Invoice")
        result = asyncio.run(run())
        assert len(result) == 2
        assert all(isinstance(m, ClassificationKeywordModel) for m in result)

    def test_returns_empty_list_when_no_keywords(self):
        async def run():
            with patch(_CFR, new_callable=AsyncMock, return_value=[]):
                return await get_keywords_by_type("Invoice")
        assert asyncio.run(run()) == []

    def test_passes_type_name_to_function(self):
        async def run():
            with patch(_CFR, new_callable=AsyncMock, return_value=[]) as mock:
                await get_keywords_by_type("Referral")
                return mock
        mock = asyncio.run(run())
        assert "Referral" in str(mock.call_args)


# ---------------------------------------------------------------------------
# get_k_keywords_by_type  (async)
# ---------------------------------------------------------------------------
class TestGetKKeywordsByType:
    def test_returns_list_of_models(self):
        rows = [_row(classificationkeywords=f"kw{i}") for i in range(3)]
        async def run():
            with patch(_CFR, new_callable=AsyncMock, return_value=rows):
                return await get_k_keywords_by_type("Invoice", k=3)
        result = asyncio.run(run())
        assert len(result) == 3
        assert all(isinstance(m, ClassificationKeywordModel) for m in result)

    def test_passes_k_to_function(self):
        async def run():
            with patch(_CFR, new_callable=AsyncMock, return_value=[]) as mock:
                await get_k_keywords_by_type("Invoice", k=5)
                return mock
        mock = asyncio.run(run())
        assert 5 in mock.call_args.args

    def test_returns_empty_list_when_no_keywords(self):
        async def run():
            with patch(_CFR, new_callable=AsyncMock, return_value=[]):
                return await get_k_keywords_by_type("Invoice", k=10)
        assert asyncio.run(run()) == []


# ---------------------------------------------------------------------------
# insert_keywords  (async)
# ---------------------------------------------------------------------------
class TestInsertKeywords:
    def test_calls_procedure_for_each_keyword(self):
        keywords = [_kw(ClassificationKeyword="kw1"), _kw(ClassificationKeyword="kw2")]
        async def run():
            with patch(_SQ, new_callable=AsyncMock, return_value=[{"typeid": 1}]):
                with patch(_CP, new_callable=AsyncMock) as mock_cp:
                    await insert_keywords("Invoice", keywords)
                    return mock_cp
        mock_cp = asyncio.run(run())
        assert mock_cp.call_count == 2

    def test_no_procedure_calls_for_empty_list(self):
        async def run():
            with patch(_SQ, new_callable=AsyncMock, return_value=[{"typeid": 1}]):
                with patch(_CP, new_callable=AsyncMock) as mock_cp:
                    await insert_keywords("Invoice", [])
                    return mock_cp
        asyncio.run(run()).assert_not_called()

    def test_returns_none(self):
        async def run():
            with patch(_SQ, new_callable=AsyncMock, return_value=[{"typeid": 1}]):
                with patch(_CP, new_callable=AsyncMock):
                    return await insert_keywords("Invoice", [_kw()])
        assert asyncio.run(run()) is None


# ---------------------------------------------------------------------------
# remove_keyword  (async)
# ---------------------------------------------------------------------------
class TestRemoveKeyword:
    def test_calls_procedure_with_keyword_id(self):
        async def run():
            with patch(_CP, new_callable=AsyncMock) as mock:
                await remove_keyword(42)
                return mock
        mock = asyncio.run(run())
        assert 42 in mock.call_args.args

    def test_returns_none(self):
        async def run():
            with patch(_CP, new_callable=AsyncMock):
                return await remove_keyword(42)
        assert asyncio.run(run()) is None


# ---------------------------------------------------------------------------
# remove_keyword_by_value  (async)
# ---------------------------------------------------------------------------
class TestRemoveKeywordByValue:
    def test_calls_procedure_with_type_and_keyword(self):
        async def run():
            with patch(_CP, new_callable=AsyncMock) as mock:
                await remove_keyword_by_value("Invoice", "net 30")
                return mock
        mock = asyncio.run(run())
        call_str = str(mock.call_args)
        assert "Invoice" in call_str
        assert "net 30" in call_str

    def test_returns_none(self):
        async def run():
            with patch(_CP, new_callable=AsyncMock):
                return await remove_keyword_by_value("Invoice", "net 30")
        assert asyncio.run(run()) is None


# ---------------------------------------------------------------------------
# update_keyword_hit  (async)
# ---------------------------------------------------------------------------
class TestUpdateKeywordHit:
    def test_calls_procedure_with_keyword_id(self):
        async def run():
            with patch(_CP, new_callable=AsyncMock) as mock:
                await update_keyword_hit(7)
                return mock
        mock = asyncio.run(run())
        assert 7 in mock.call_args.args

    def test_returns_none(self):
        async def run():
            with patch(_CP, new_callable=AsyncMock):
                return await update_keyword_hit(7)
        assert asyncio.run(run()) is None


# ---------------------------------------------------------------------------
# update_keyword_miss  (async)
# ---------------------------------------------------------------------------
class TestUpdateKeywordMiss:
    def test_calls_procedure_with_keyword_id(self):
        async def run():
            with patch(_CP, new_callable=AsyncMock) as mock:
                await update_keyword_miss(7)
                return mock
        mock = asyncio.run(run())
        assert 7 in mock.call_args.args

    def test_returns_none(self):
        async def run():
            with patch(_CP, new_callable=AsyncMock):
                return await update_keyword_miss(7)
        assert asyncio.run(run()) is None


# ---------------------------------------------------------------------------
# deactivate_stale_keywords  (async)
# ---------------------------------------------------------------------------
class TestDeactivateStaleKeywords:
    def test_returns_count_of_deactivated_keywords(self):
        async def run():
            with patch(_CFR, new_callable=AsyncMock, return_value=[{"deactivate_stale_keywords": 5}]):
                return await deactivate_stale_keywords()
        assert asyncio.run(run()) == 5

    def test_returns_zero_when_no_stale_keywords(self):
        async def run():
            with patch(_CFR, new_callable=AsyncMock, return_value=[]):
                return await deactivate_stale_keywords()
        assert asyncio.run(run()) == 0
