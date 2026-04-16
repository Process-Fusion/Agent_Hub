"""
Unit tests for src/DAL/classification_trust_system_DA.py.

All tests mock execute_query so no real database is required.
The trust score is defined as:  net_hits = HitCount - MissCount
A type is trusted when net_hits >= min_hits (default 3).
"""

from unittest.mock import call, patch

import pytest

from src.DAL.classification_trust_system_DA import (
    get_all_trust,
    get_trust_by_type,
    increment_hit_count,
    increment_miss_count,
    is_trusted,
    reset_trust,
    update_hit_count,
    update_miss_count,
)

_EQ = "src.DAL.classification_trust_system_DA.execute_query"


# ---------------------------------------------------------------------------
# get_trust_by_type
# ---------------------------------------------------------------------------
class TestGetTrustByType:
    def test_returns_row_dict_when_found(self):
        row = {
            "trustid": 1,
            "classificationtype": "Invoice",
            "hitcount": 5,
            "misscount": 1,
            "createddate": None,
            "modifieddate": None,
        }
        with patch(_EQ, return_value=[row]):
            result = get_trust_by_type("Invoice")
        assert result == row

    def test_returns_none_when_type_not_found(self):
        with patch(_EQ, return_value=[]):
            result = get_trust_by_type("Unknown")
        assert result is None

    def test_passes_type_name_to_query(self):
        with patch(_EQ, return_value=[]) as mock:
            get_trust_by_type("Purchase Order")
        _, kwargs = mock.call_args
        params = mock.call_args[0][1] if len(mock.call_args[0]) > 1 else mock.call_args[1].get("params", {})
        # type name appears somewhere in the call arguments
        assert "Purchase Order" in str(mock.call_args)


# ---------------------------------------------------------------------------
# get_all_trust
# ---------------------------------------------------------------------------
class TestGetAllTrust:
    def test_returns_dict_keyed_by_type(self):
        rows = [
            {"classificationtype": "Invoice", "hitcount": 5, "misscount": 1},
            {"classificationtype": "Purchase Order", "hitcount": 3, "misscount": 0},
        ]
        with patch(_EQ, return_value=rows):
            result = get_all_trust()
        assert result == {
            "Invoice": {"HitCount": 5, "MissCount": 1},
            "Purchase Order": {"HitCount": 3, "MissCount": 0},
        }

    def test_returns_empty_dict_when_no_records(self):
        with patch(_EQ, return_value=[]):
            result = get_all_trust()
        assert result == {}

    def test_single_type(self):
        rows = [{"classificationtype": "Fax_Monitoring", "hitcount": 10, "misscount": 2}]
        with patch(_EQ, return_value=rows):
            result = get_all_trust()
        assert "Fax_Monitoring" in result
        assert result["Fax_Monitoring"]["HitCount"] == 10
        assert result["Fax_Monitoring"]["MissCount"] == 2


# ---------------------------------------------------------------------------
# is_trusted
# ---------------------------------------------------------------------------
class TestIsTrusted:
    def test_trusted_when_net_hits_exceed_threshold(self):
        with patch(_EQ, return_value=[{"hitcount": 5, "misscount": 1}]):
            assert is_trusted("Invoice") is True  # net = 4 >= 3

    def test_not_trusted_when_net_hits_below_threshold(self):
        with patch(_EQ, return_value=[{"hitcount": 2, "misscount": 1}]):
            assert is_trusted("Invoice") is False  # net = 1 < 3

    def test_trusted_at_exact_threshold(self):
        with patch(_EQ, return_value=[{"hitcount": 3, "misscount": 0}]):
            assert is_trusted("Invoice") is True  # net = 3 == 3

    def test_not_trusted_one_below_threshold(self):
        with patch(_EQ, return_value=[{"hitcount": 3, "misscount": 1}]):
            assert is_trusted("Invoice") is False  # net = 2 < 3

    def test_not_trusted_when_type_not_found(self):
        with patch(_EQ, return_value=[]):
            assert is_trusted("Unknown") is False

    def test_misses_reduce_trust_score(self):
        with patch(_EQ, return_value=[{"hitcount": 10, "misscount": 8}]):
            assert is_trusted("Invoice") is False  # net = 2 < 3

    def test_custom_min_hits_parameter(self):
        with patch(_EQ, return_value=[{"hitcount": 7, "misscount": 2}]):
            assert is_trusted("Invoice", min_hits=5) is True  # net = 5 >= 5

    def test_custom_min_hits_not_met(self):
        with patch(_EQ, return_value=[{"hitcount": 7, "misscount": 2}]):
            assert is_trusted("Invoice", min_hits=6) is False  # net = 5 < 6

    def test_zero_hits_zero_misses_not_trusted(self):
        with patch(_EQ, return_value=[{"hitcount": 0, "misscount": 0}]):
            assert is_trusted("Invoice") is False  # net = 0 < 3


# ---------------------------------------------------------------------------
# increment_hit_count / increment_miss_count
# ---------------------------------------------------------------------------
class TestIncrementCounts:
    def test_increment_hit_count_returns_row_count(self):
        with patch(_EQ, return_value=1) as mock:
            result = increment_hit_count("Invoice")
        assert result == 1
        mock.assert_called_once()

    def test_increment_hit_count_passes_type_name(self):
        with patch(_EQ, return_value=1) as mock:
            increment_hit_count("Referral")
        assert "Referral" in str(mock.call_args)

    def test_increment_miss_count_returns_row_count(self):
        with patch(_EQ, return_value=1) as mock:
            result = increment_miss_count("Invoice")
        assert result == 1
        mock.assert_called_once()

    def test_increment_miss_count_passes_type_name(self):
        with patch(_EQ, return_value=1) as mock:
            increment_miss_count("Purchase Order")
        assert "Purchase Order" in str(mock.call_args)

    def test_increment_returns_zero_when_type_not_found(self):
        with patch(_EQ, return_value=0):
            assert increment_hit_count("Ghost") == 0


# ---------------------------------------------------------------------------
# update_hit_count / update_miss_count
# ---------------------------------------------------------------------------
class TestUpdateCounts:
    def test_update_hit_count_passes_value_and_type(self):
        with patch(_EQ, return_value=1) as mock:
            result = update_hit_count("Invoice", 10)
        assert result == 1
        assert "10" in str(mock.call_args)
        assert "Invoice" in str(mock.call_args)

    def test_update_miss_count_passes_value_and_type(self):
        with patch(_EQ, return_value=1) as mock:
            result = update_miss_count("Invoice", 3)
        assert result == 1
        assert "3" in str(mock.call_args)
        assert "Invoice" in str(mock.call_args)

    def test_update_hit_count_to_zero(self):
        with patch(_EQ, return_value=1) as mock:
            update_hit_count("Invoice", 0)
        assert "0" in str(mock.call_args)


# ---------------------------------------------------------------------------
# reset_trust
# ---------------------------------------------------------------------------
class TestResetTrust:
    def test_reset_returns_row_count(self):
        with patch(_EQ, return_value=1) as mock:
            result = reset_trust("Invoice")
        assert result == 1
        mock.assert_called_once()

    def test_reset_passes_type_name(self):
        with patch(_EQ, return_value=1) as mock:
            reset_trust("Purchase Order")
        assert "Purchase Order" in str(mock.call_args)

    def test_reset_returns_zero_when_type_not_found(self):
        with patch(_EQ, return_value=0):
            assert reset_trust("Ghost") == 0
