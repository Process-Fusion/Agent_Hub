"""
Integration tests for POST /api/document-classify/classify.

These tests exercise the real DocumentClassifyAgent (real LLM + real DB).
They are skipped automatically when the required env vars are absent.

Required env vars:
  OPENAI_API_KEY             – Moonshot API key (ChatOpenAI is pointed at api.moonshot.ai/v1)
  POSTGRES_CONNECTION_STRING – asyncpg-compatible Postgres URL
                               e.g. postgresql://user:pass@host:5432/dbname

Known issue: agent.arun() does not return `matched_keyword_ids`, so the
controller will raise KeyError -> 500 until that is fixed.
"""

import asyncio
import os
import sys
from pathlib import Path

import httpx

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
import pytest
from fastapi import FastAPI

from src.utils.pdf_utils import pdf_to_base64_images
from dotenv import load_dotenv

load_dotenv()
# ---------------------------------------------------------------------------
# Skip the entire module when integration env vars are absent
# ---------------------------------------------------------------------------
pytestmark = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY") or not os.getenv("POSTGRES_CONNECTION_STRING"),
    reason=(
        "Integration env vars not set: OPENAI_API_KEY and "
        "POSTGRES_CONNECTION_STRING are both required"
    ),
)

_URL = "/api/document-classify/classify"

_PDF_NAME = "66B9FFF2-39CB-437E-A923-0A8EECBC757C-463242-IF.pdf"
_PDF_PATH = f"tests/assets/{_PDF_NAME}"
_PDF_IMAGES = pdf_to_base64_images(_PDF_PATH, dpi=150)

_PAYLOAD = {
    "document_name": _PDF_NAME,
    "request": "classify this document",
    "image_bytes": _PDF_IMAGES,
}


# ---------------------------------------------------------------------------
# Single event loop shared across all fixtures and tests in this module.
# asyncpg pool connections are bound to the loop they were created on;
# using asyncio.run() (which creates+closes a new loop each time) would
# make those connections invalid by the time the tests run.
# ---------------------------------------------------------------------------
_loop = asyncio.new_event_loop()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def integration_app():
    """Start the real DB pool and agent once for the whole module, then tear down."""
    from main import app
    from src.infrastructure.postgres_db import init_pool, close_pool
    from src.agents.document_classify_agent.agent import DocumentClassifyAgent

    async def _startup():
        await init_pool()
        app.state.agents = {"document_classify_agent": DocumentClassifyAgent()}

    _loop.run_until_complete(_startup())
    yield app
    _loop.run_until_complete(close_pool())
    _loop.close()


@pytest.fixture(scope="module")
def classify_response(integration_app):
    """Make one real classify request and share the response across all tests."""
    return _req(integration_app, "post", _URL, json=_PAYLOAD)


def _req(app: FastAPI, method: str, path: str, **kwargs) -> httpx.Response:
    async def _call():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            return await getattr(client, method)(path, **kwargs)

    return _loop.run_until_complete(_call())


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
class TestClassifyIntegration:
    def test_returns_200_or_202(self, classify_response):
        assert classify_response.status_code in (200, 202), (
            f"Expected 200 or 202, got {classify_response.status_code}: "
            f"{classify_response.text}"
        )

    def test_200_response_has_required_fields(self, classify_response):
        if classify_response.status_code != 200:
            pytest.skip("Agent returned interrupt (202) — skipping 200-only assertions")
        data = classify_response.json()
        for field in ("document_name", "classification_type", "confidence_score",
                      "reasoning", "matched_keyword_ids"):
            assert field in data, f"Missing field: {field}"

    def test_202_response_has_awaiting_human_status(self, classify_response):
        if classify_response.status_code != 202:
            pytest.skip("Agent returned direct result (200) — skipping 202-only assertions")
        data = classify_response.json()
        assert data["status"] == "awaiting_human"
        assert "interrupt" in data

    def test_document_name_echoed(self, classify_response):
        if classify_response.status_code != 200:
            pytest.skip("Agent returned interrupt (202)")
        assert classify_response.json()["document_name"] == "integration_test_invoice.pdf"

    def test_confidence_score_in_valid_range(self, classify_response):
        if classify_response.status_code != 200:
            pytest.skip("Agent returned interrupt (202)")
        score = classify_response.json()["confidence_score"]
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_classification_type_is_nonempty_string(self, classify_response):
        if classify_response.status_code != 200:
            pytest.skip("Agent returned interrupt (202)")
        classification_type = classify_response.json()["classification_type"]
        assert isinstance(classification_type, str)
        assert classification_type.strip()

    def test_matched_keyword_ids_is_list(self, classify_response):
        if classify_response.status_code != 200:
            pytest.skip("Agent returned interrupt (202)")
        assert isinstance(classify_response.json()["matched_keyword_ids"], list)

    # Pydantic validation — no LLM call needed
    def test_missing_document_name_returns_422(self, integration_app):
        resp = _req(
            integration_app,
            "post",
            _URL,
            json={"request": "classify", "image_bytes": _PDF_IMAGES},
        )
        assert resp.status_code == 422

    def test_missing_request_returns_422(self, integration_app):
        resp = _req(
            integration_app,
            "post",
            _URL,
            json={"document_name": "file.pdf", "image_bytes": _PDF_IMAGES},
        )
        assert resp.status_code == 422

    def test_missing_image_bytes_returns_422(self, integration_app):
        resp = _req(
            integration_app,
            "post",
            _URL,
            json={"document_name": "file.pdf", "request": "classify"},
        )
        assert resp.status_code == 422

    def test_empty_body_returns_422(self, integration_app):
        assert _req(integration_app, "post", _URL, json={}).status_code == 422