"""
Unit tests for src/DAL/classification_trust_system_DA.py.

Read functions mock select_query; mutation functions mock call_procedure.
Trust score: net_hits = HitCount - MissCount; trusted when net_hits >= min_hits (default 3).
"""

import asyncio
from unittest.mock import AsyncMock, patch

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

_SQ = "src.DAL.classification_trust_system_DA.select_query"
_CP = "src.DAL.classification_trust_system_DA.call_procedure"


# ---------------------------------------------------------------------------
# get_trust_by_type
# ---------------------------------------------------------------------------
class TestGetTrustByType:
    def test_returns_row_dict_when_found(self):
        row = {"trustid": 1, "classificationtype": "Invoice", "hitcount": 5,
               "misscount": 1, "createddate": None, "modifieddate": None}
        async def run():
            with patch(_SQ, new_callable=AsyncMock, return_value=[row]):
                return await get_trust_by_type("Invoice")
        assert asyncio.run(run()) == row

    def test_returns_none_when_type_not_found(self):
        async def run():
            with patch(_SQ, new_callable=AsyncMock, return_value=[]):
                return await get_trust_by_type("Unknown")
        assert asyncio.run(run()) is None

    def test_passes_type_name_to_query(self):
        async def run():
            with patch(_SQ, new_callable=AsyncMock, return_value=[]) as mock:
                await get_trust_by_type("Purchase Order")
                return mock
        mock = asyncio.run(run())
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
        async def run():
            with patch(_SQ, new_callable=AsyncMock, return_value=rows):
                return await get_all_trust()
        assert asyncio.run(run()) == {
            "Invoice": {"HitCount": 5, "MissCount": 1},
            "Purchase Order": {"HitCount": 3, "MissCount": 0},
        }

    def test_returns_empty_dict_when_no_records(self):
        async def run():
            with patch(_SQ, new_callable=AsyncMock, return_value=[]):
                return await get_all_trust()
        assert asyncio.run(run()) == {}

    def test_single_type(self):
        rows = [{"classificationtype": "Fax_Monitoring", "hitcount": 10, "misscount": 2}]
        async def run():
            with patch(_SQ, new_callable=AsyncMock, return_value=rows):
                return await get_all_trust()
        result = asyncio.run(run())
        assert result["Fax_Monitoring"] == {"HitCount": 10, "MissCount": 2}


# ---------------------------------------------------------------------------
# is_trusted
# ---------------------------------------------------------------------------
class TestIsTrusted:
    def test_trusted_when_net_hits_exceed_threshold(self):
        async def run():
            with patch(_SQ, new_callable=AsyncMock, return_value=[{"hitcount": 5, "misscount": 1}]):
                return await is_trusted("Invoice")
        assert asyncio.run(run()) is True  # net = 4 >= 3

    def test_not_trusted_when_net_hits_below_threshold(self):
        async def run():
            with patch(_SQ, new_callable=AsyncMock, return_value=[{"hitcount": 2, "misscount": 1}]):
                return await is_trusted("Invoice")
        assert asyncio.run(run()) is False  # net = 1 < 3

    def test_trusted_at_exact_threshold(self):
        async def run():
            with patch(_SQ, new_callable=AsyncMock, return_value=[{"hitcount": 3, "misscount": 0}]):
                return await is_trusted("Invoice")
        assert asyncio.run(run()) is True  # net = 3 == 3

    def test_not_trusted_one_below_threshold(self):
        async def run():
            with patch(_SQ, new_callable=AsyncMock, return_value=[{"hitcount": 3, "misscount": 1}]):
                return await is_trusted("Invoice")
        assert asyncio.run(run()) is False  # net = 2 < 3

    def test_not_trusted_when_type_not_found(self):
        async def run():
            with patch(_SQ, new_callable=AsyncMock, return_value=[]):
                return await is_trusted("Unknown")
        assert asyncio.run(run()) is False

    def test_misses_reduce_trust_score(self):
        async def run():
            with patch(_SQ, new_callable=AsyncMock, return_value=[{"hitcount": 10, "misscount": 8}]):
                return await is_trusted("Invoice")
        assert asyncio.run(run()) is False  # net = 2 < 3

    def test_custom_min_hits_parameter(self):
        async def run():
            with patch(_SQ, new_callable=AsyncMock, return_value=[{"hitcount": 7, "misscount": 2}]):
                return await is_trusted("Invoice", min_hits=5)
        assert asyncio.run(run()) is True  # net = 5 >= 5

    def test_custom_min_hits_not_met(self):
        async def run():
            with patch(_SQ, new_callable=AsyncMock, return_value=[{"hitcount": 7, "misscount": 2}]):
                return await is_trusted("Invoice", min_hits=6)
        assert asyncio.run(run()) is False  # net = 5 < 6

    def test_zero_hits_zero_misses_not_trusted(self):
        async def run():
            with patch(_SQ, new_callable=AsyncMock, return_value=[{"hitcount": 0, "misscount": 0}]):
                return await is_trusted("Invoice")
        assert asyncio.run(run()) is False  # net = 0 < 3


# ---------------------------------------------------------------------------
# increment_hit_count / increment_miss_count
# ---------------------------------------------------------------------------
class TestIncrementCounts:
    def test_increment_hit_count_calls_procedure(self):
        async def run():
            with patch(_CP, new_callable=AsyncMock) as mock:
                await increment_hit_count("Invoice")
                return mock
        asyncio.run(run()).assert_called_once()

    def test_increment_hit_count_passes_type_name(self):
        async def run():
            with patch(_CP, new_callable=AsyncMock) as mock:
                await increment_hit_count("Referral")
                return mock
        mock = asyncio.run(run())
        assert "Referral" in str(mock.call_args)

    def test_increment_miss_count_calls_procedure(self):
        async def run():
            with patch(_CP, new_callable=AsyncMock) as mock:
                await increment_miss_count("Invoice")
                return mock
        asyncio.run(run()).assert_called_once()

    def test_increment_miss_count_passes_type_name(self):
        async def run():
            with patch(_CP, new_callable=AsyncMock) as mock:
                await increment_miss_count("Purchase Order")
                return mock
        mock = asyncio.run(run())
        assert "Purchase Order" in str(mock.call_args)

    def test_increment_hit_returns_none(self):
        async def run():
            with patch(_CP, new_callable=AsyncMock):
                return await increment_hit_count("Invoice")
        assert asyncio.run(run()) is None

    def test_increment_miss_returns_none(self):
        async def run():
            with patch(_CP, new_callable=AsyncMock):
                return await increment_miss_count("Invoice")
        assert asyncio.run(run()) is None


# ---------------------------------------------------------------------------
# update_hit_count / update_miss_count
# ---------------------------------------------------------------------------
class TestUpdateCounts:
    def test_update_hit_count_passes_value_and_type(self):
        async def run():
            with patch(_CP, new_callable=AsyncMock) as mock:
                await update_hit_count("Invoice", 10)
                return mock
        mock = asyncio.run(run())
        call_str = str(mock.call_args)
        assert "10" in call_str
        assert "Invoice" in call_str

    def test_update_miss_count_passes_value_and_type(self):
        async def run():
            with patch(_CP, new_callable=AsyncMock) as mock:
                await update_miss_count("Invoice", 3)
                return mock
        mock = asyncio.run(run())
        call_str = str(mock.call_args)
        assert "3" in call_str
        assert "Invoice" in call_str

    def test_update_hit_count_to_zero(self):
        async def run():
            with patch(_CP, new_callable=AsyncMock) as mock:
                await update_hit_count("Invoice", 0)
                return mock
        assert "0" in str(asyncio.run(run()).call_args)

    def test_update_returns_none(self):
        async def run():
            with patch(_CP, new_callable=AsyncMock):
                return await update_hit_count("Invoice", 5)
        assert asyncio.run(run()) is None


# ---------------------------------------------------------------------------
# reset_trust
# ---------------------------------------------------------------------------
class TestResetTrust:
    def test_reset_calls_procedure(self):
        async def run():
            with patch(_CP, new_callable=AsyncMock) as mock:
                await reset_trust("Invoice")
                return mock
        asyncio.run(run()).assert_called_once()

    def test_reset_passes_type_name(self):
        async def run():
            with patch(_CP, new_callable=AsyncMock) as mock:
                await reset_trust("Purchase Order")
                return mock
        mock = asyncio.run(run())
        assert "Purchase Order" in str(mock.call_args)

    def test_reset_returns_none(self):
        async def run():
            with patch(_CP, new_callable=AsyncMock):
                return await reset_trust("Invoice")
        assert asyncio.run(run()) is None
