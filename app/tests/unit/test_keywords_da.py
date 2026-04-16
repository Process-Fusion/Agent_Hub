"""
Unit tests for src/DAL/classification_keywords_DA.py.

All tests mock execute_query so no real database is required.
"""

from unittest.mock import patch

import pytest

from src.DAL.classification_keywords_DA import (
    _ensure_type_exists,
    _get_type_id,
    get_all_keywords,
    get_keywords_by_type,
    hard_delete_keyword,
    insert_keyword,
    insert_keywords,
    remove_keyword,
    remove_keyword_by_value,
)

_EQ = "src.DAL.classification_keywords_DA.execute_query"


# ---------------------------------------------------------------------------
# _get_type_id
# ---------------------------------------------------------------------------
class TestGetTypeId:
    def test_returns_id_when_type_found(self):
        with patch(_EQ, return_value=[{"typeid": 42}]):
            assert _get_type_id("Invoice") == 42

    def test_returns_none_when_type_not_found(self):
        with patch(_EQ, return_value=[]):
            assert _get_type_id("Unknown") is None

    def test_passes_type_name_to_query(self):
        with patch(_EQ, return_value=[{"typeid": 1}]) as mock:
            _get_type_id("Purchase Order")
        assert "Purchase Order" in str(mock.call_args)


# ---------------------------------------------------------------------------
# _ensure_type_exists
# ---------------------------------------------------------------------------
class TestEnsureTypeExists:
    def test_returns_existing_type_id_without_inserting(self):
        with patch(_EQ, return_value=[{"typeid": 5}]) as mock:
            result = _ensure_type_exists("Invoice")
        assert result == 5
        mock.assert_called_once()  # only the SELECT, no INSERT

    def test_inserts_and_returns_new_id_when_type_missing(self):
        # First call: SELECT returns nothing; second call: INSERT returns new id
        with patch(_EQ, side_effect=[[], [{"typeid": 99}]]) as mock:
            result = _ensure_type_exists("NewType")
        assert result == 99
        assert mock.call_count == 2

    def test_returns_zero_when_insert_returns_nothing(self):
        with patch(_EQ, side_effect=[[], []]):
            result = _ensure_type_exists("BadType")
        assert result == 0


# ---------------------------------------------------------------------------
# get_all_keywords
# ---------------------------------------------------------------------------
class TestGetAllKeywords:
    def test_groups_keywords_by_type(self):
        rows = [
            {"classificationtype": "Invoice", "classificationkeywords": "invoice"},
            {"classificationtype": "Invoice", "classificationkeywords": "payment due"},
            {"classificationtype": "Purchase Order", "classificationkeywords": "PO number"},
        ]
        with patch(_EQ, return_value=rows):
            result = get_all_keywords()
        assert result == {
            "Invoice": ["invoice", "payment due"],
            "Purchase Order": ["PO number"],
        }

    def test_returns_empty_dict_when_no_keywords(self):
        with patch(_EQ, return_value=[]):
            assert get_all_keywords() == {}

    def test_preserves_insertion_order_within_type(self):
        rows = [
            {"classificationtype": "Invoice", "classificationkeywords": "first"},
            {"classificationtype": "Invoice", "classificationkeywords": "second"},
            {"classificationtype": "Invoice", "classificationkeywords": "third"},
        ]
        with patch(_EQ, return_value=rows):
            result = get_all_keywords()
        assert result["Invoice"] == ["first", "second", "third"]

    def test_multiple_types_independent(self):
        rows = [
            {"classificationtype": "A", "classificationkeywords": "kw_a"},
            {"classificationtype": "B", "classificationkeywords": "kw_b"},
        ]
        with patch(_EQ, return_value=rows):
            result = get_all_keywords()
        assert len(result) == 2
        assert result["A"] == ["kw_a"]
        assert result["B"] == ["kw_b"]


# ---------------------------------------------------------------------------
# get_keywords_by_type
# ---------------------------------------------------------------------------
class TestGetKeywordsByType:
    def test_returns_list_of_keywords(self):
        rows = [
            {"classificationkeywords": "invoice"},
            {"classificationkeywords": "balance due"},
            {"classificationkeywords": "payment terms"},
        ]
        with patch(_EQ, return_value=rows):
            result = get_keywords_by_type("Invoice")
        assert result == ["invoice", "balance due", "payment terms"]

    def test_returns_empty_list_when_no_keywords(self):
        with patch(_EQ, return_value=[]):
            result = get_keywords_by_type("Invoice")
        assert result == []

    def test_passes_type_name_to_query(self):
        with patch(_EQ, return_value=[]) as mock:
            get_keywords_by_type("Referral")
        assert "Referral" in str(mock.call_args)


# ---------------------------------------------------------------------------
# insert_keyword
# ---------------------------------------------------------------------------
class TestInsertKeyword:
    def test_returns_new_keyword_id(self):
        # First call: _ensure_type_exists SELECT; second: INSERT keyword
        with patch(_EQ, side_effect=[[{"typeid": 1}], [{"keywordid": 10}]]):
            result = insert_keyword("Invoice", "net 30")
        assert result == 10

    def test_returns_zero_when_insert_returns_nothing(self):
        with patch(_EQ, side_effect=[[{"typeid": 1}], []]):
            result = insert_keyword("Invoice", "net 30")
        assert result == 0

    def test_passes_keyword_text_to_query(self):
        with patch(_EQ, side_effect=[[{"typeid": 1}], [{"keywordid": 5}]]) as mock:
            insert_keyword("Invoice", "balance due")
        call_strings = " ".join(str(c) for c in mock.call_args_list)
        assert "balance due" in call_strings


# ---------------------------------------------------------------------------
# insert_keywords
# ---------------------------------------------------------------------------
class TestInsertKeywords:
    def test_returns_list_of_ids(self):
        with patch(
            _EQ,
            side_effect=[
                [{"typeid": 1}],       # _ensure_type_exists
                [{"keywordid": 10}],   # first keyword
                [{"keywordid": 11}],   # second keyword
            ],
        ):
            result = insert_keywords("Invoice", ["net 30", "balance"])
        assert result == [10, 11]

    def test_returns_empty_list_for_empty_input(self):
        # _ensure_type_exists is still called for the type lookup
        with patch(_EQ, return_value=[{"typeid": 1}]):
            result = insert_keywords("Invoice", [])
        assert result == []

    def test_skips_failed_inserts(self):
        with patch(
            _EQ,
            side_effect=[
                [{"typeid": 1}],
                [{"keywordid": 7}],
                [],                 # second insert fails
                [{"keywordid": 9}],
            ],
        ):
            result = insert_keywords("Invoice", ["kw1", "kw2", "kw3"])
        assert result == [7, 9]


# ---------------------------------------------------------------------------
# remove_keyword (soft delete by ID)
# ---------------------------------------------------------------------------
class TestRemoveKeyword:
    def test_returns_row_count_on_success(self):
        with patch(_EQ, return_value=1) as mock:
            result = remove_keyword(42)
        assert result == 1
        mock.assert_called_once()

    def test_passes_keyword_id_to_query(self):
        with patch(_EQ, return_value=1) as mock:
            remove_keyword(42)
        assert "42" in str(mock.call_args)

    def test_returns_zero_when_id_not_found(self):
        with patch(_EQ, return_value=0):
            assert remove_keyword(9999) == 0


# ---------------------------------------------------------------------------
# remove_keyword_by_value (soft delete by type + keyword text)
# ---------------------------------------------------------------------------
class TestRemoveKeywordByValue:
    def test_returns_row_count_on_success(self):
        with patch(_EQ, return_value=2) as mock:
            result = remove_keyword_by_value("Invoice", "net 30")
        assert result == 2
        mock.assert_called_once()

    def test_passes_type_and_keyword_to_query(self):
        with patch(_EQ, return_value=1) as mock:
            remove_keyword_by_value("Purchase Order", "PO number")
        call_str = str(mock.call_args)
        assert "Purchase Order" in call_str
        assert "PO number" in call_str

    def test_returns_zero_when_not_found(self):
        with patch(_EQ, return_value=0):
            assert remove_keyword_by_value("Invoice", "ghost keyword") == 0


# ---------------------------------------------------------------------------
# hard_delete_keyword
# ---------------------------------------------------------------------------
class TestHardDeleteKeyword:
    def test_returns_row_count_on_success(self):
        with patch(_EQ, return_value=1) as mock:
            result = hard_delete_keyword(42)
        assert result == 1
        mock.assert_called_once()

    def test_passes_keyword_id_to_query(self):
        with patch(_EQ, return_value=1) as mock:
            hard_delete_keyword(99)
        assert "99" in str(mock.call_args)

    def test_returns_zero_when_id_not_found(self):
        with patch(_EQ, return_value=0):
            assert hard_delete_keyword(9999) == 0
