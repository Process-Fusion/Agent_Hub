"""
Unit tests for controllers/document_classify_controller.py.

Uses httpx.AsyncClient + ASGITransport directly to avoid the version
incompatibility between starlette <=0.27 and httpx >=0.25 in TestClient.

NOTE — known bug in POST /type:
  The endpoint function is named `add_classification_type`, which shadows the
  imported service function of the same name. Without patching, the endpoint
  calls itself recursively and raises RecursionError (→ 500). Tests patch the
  module-level name so the mock is resolved at call time, exercising the
  intended endpoint logic.
"""

import asyncio
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi import FastAPI

from controllers.document_classify_controller import router

# Minimal app — no lifespan / DB pool
_app = FastAPI()
_app.include_router(router)

_transport = httpx.ASGITransport(app=_app)
_BASE = "http://test"


def _req(method: str, path: str, **kwargs) -> httpx.Response:
    """Run an async httpx request against the test app synchronously."""

    async def _call():
        async with httpx.AsyncClient(
            transport=_transport, base_url=_BASE
        ) as client:
            return await getattr(client, method)(path, **kwargs)

    return asyncio.run(_call())


# ---------------------------------------------------------------------------
# POST /api/document-classify/classify
# ---------------------------------------------------------------------------
class TestClassifyEndpoint:
    _url = "/api/document-classify/classify"

    _payload = {
        "document_name": "invoice.pdf",
        "request": "classify this document",
        "image_bytes": ["ZmFrZWJ5dGVz"],  # base64("fakebytes")
    }

    _agent_response = {
        "classification_type": "Invoice",
        "confidence_score": 0.95,
        "reasoning": "Document contains invoice-related keywords.",
        "matched_keyword_ids": [1, 2, 3],
    }

    @pytest.fixture(autouse=True)
    def _mock_agent(self):
        mock_agent = AsyncMock()
        mock_agent.arun.return_value = self._agent_response
        _app.state.agents = {"document_classify_agent": mock_agent}
        yield mock_agent
        del _app.state.agents

    def test_returns_200(self):
        assert _req("post", self._url, json=self._payload).status_code == 200

    def test_response_contains_required_fields(self):
        data = _req("post", self._url, json=self._payload).json()
        assert "document_name" in data
        assert "classification_type" in data
        assert "confidence_score" in data
        assert "reasoning" in data
        assert "matched_keyword_ids" in data

    def test_document_name_echoed_in_response(self):
        data = _req("post", self._url, json=self._payload).json()
        assert data["document_name"] == "invoice.pdf"

    def test_confidence_score_is_float(self):
        data = _req("post", self._url, json=self._payload).json()
        assert isinstance(data["confidence_score"], float)

    def test_matched_keyword_ids_is_list(self):
        data = _req("post", self._url, json=self._payload).json()
        assert isinstance(data["matched_keyword_ids"], list)

    def test_returns_202_on_graph_interrupt(self):
        from langgraph.errors import GraphInterrupt
        mock_agent = AsyncMock()
        mock_agent.arun.side_effect = GraphInterrupt({"question": "What type?"})
        _app.state.agents = {"document_classify_agent": mock_agent}
        resp = _req("post", self._url, json=self._payload)
        assert resp.status_code == 202
        assert resp.json()["status"] == "awaiting_human"

    def test_returns_500_on_agent_error(self):
        mock_agent = AsyncMock()
        mock_agent.arun.side_effect = Exception("Agent failure")
        _app.state.agents = {"document_classify_agent": mock_agent}
        resp = _req("post", self._url, json=self._payload)
        assert resp.status_code == 500

    def test_missing_document_name_returns_422(self):
        resp = _req(
            "post",
            self._url,
            json={"request": "classify", "image_bytes": ["ZmFrZQ=="]},
        )
        assert resp.status_code == 422

    def test_missing_request_returns_422(self):
        resp = _req(
            "post",
            self._url,
            json={"document_name": "file.pdf", "image_bytes": ["ZmFrZQ=="]},
        )
        assert resp.status_code == 422

    def test_missing_image_bytes_returns_422(self):
        resp = _req(
            "post",
            self._url,
            json={"document_name": "file.pdf", "request": "classify"},
        )
        assert resp.status_code == 422

    def test_empty_body_returns_422(self):
        assert _req("post", self._url, json={}).status_code == 422


# ---------------------------------------------------------------------------
# GET /api/document-classify/types
# ---------------------------------------------------------------------------
class TestGetClassificationTypesEndpoint:
    _url = "/api/document-classify/types"

    def test_returns_200_and_list(self):
        expected = ["Invoice", "Purchase Order", "Referral"]
        with patch(
            "controllers.document_classify_controller.get_all_classification_types",
            new=AsyncMock(return_value=expected),
        ):
            response = _req("get", self._url)
        assert response.status_code == 200
        assert response.json() == expected

    def test_returns_empty_list(self):
        with patch(
            "controllers.document_classify_controller.get_all_classification_types",
            new=AsyncMock(return_value=[]),
        ):
            response = _req("get", self._url)
        assert response.status_code == 200
        assert response.json() == []

    def test_returns_500_on_service_error(self):
        with patch(
            "controllers.document_classify_controller.get_all_classification_types",
            new=AsyncMock(side_effect=Exception("DB unavailable")),
        ):
            response = _req("get", self._url)
        assert response.status_code == 500


# ---------------------------------------------------------------------------
# GET /api/document-classify/keywords/{classification_type}
# ---------------------------------------------------------------------------
class TestGetClassificationKeywordsEndpoint:
    _base = "/api/document-classify/keywords"

    def test_returns_keywords_for_type(self):
        keywords = ["invoice", "payment due", "balance"]
        with patch(
            "controllers.document_classify_controller.get_classification_keywords_by_type",
            new=AsyncMock(return_value=keywords),
        ):
            response = _req("get", f"{self._base}/Invoice")
        assert response.status_code == 200
        assert response.json() == keywords

    def test_returns_empty_list_for_unknown_type(self):
        with patch(
            "controllers.document_classify_controller.get_classification_keywords_by_type",
            new=AsyncMock(return_value=[]),
        ):
            response = _req("get", f"{self._base}/Unknown")
        assert response.status_code == 200
        assert response.json() == []

    def test_type_passed_as_path_param(self):
        with patch(
            "controllers.document_classify_controller.get_classification_keywords_by_type",
            new=AsyncMock(return_value=[]),
        ) as mock:
            _req("get", f"{self._base}/Invoice")
        mock.assert_called_once_with("Invoice")

    def test_url_encoded_type_is_decoded(self):
        with patch(
            "controllers.document_classify_controller.get_classification_keywords_by_type",
            new=AsyncMock(return_value=[]),
        ) as mock:
            _req("get", f"{self._base}/Purchase%20Order")
        mock.assert_called_once_with("Purchase Order")

    def test_returns_500_on_service_error(self):
        with patch(
            "controllers.document_classify_controller.get_classification_keywords_by_type",
            new=AsyncMock(side_effect=Exception("DB error")),
        ):
            response = _req("get", f"{self._base}/Invoice")
        assert response.status_code == 500


# ---------------------------------------------------------------------------
# POST /api/document-classify/type
# ---------------------------------------------------------------------------
class TestAddClassificationTypeEndpoint:
    _url = "/api/document-classify/type"

    # NOTE: Without patching, this endpoint recurses into itself (naming
    # conflict: the endpoint function shadows the imported service function).
    # All tests below patch the module-level name so the mock is resolved.

    def test_returns_200_with_success_message(self):
        with patch(
            "controllers.document_classify_controller.add_classification_type",
            new=AsyncMock(return_value=None),
        ):
            response = _req(
                "post",
                self._url,
                json={"classification_type": "NewType", "description": "A new type"},
            )
        assert response.status_code == 200
        assert response.json()["message"] == "Classification type added successfully"

    def test_description_is_optional(self):
        with patch(
            "controllers.document_classify_controller.add_classification_type",
            new=AsyncMock(return_value=None),
        ):
            response = _req(
                "post", self._url, json={"classification_type": "NewType"}
            )
        assert response.status_code == 200

    def test_missing_classification_type_returns_422(self):
        response = _req(
            "post", self._url, json={"description": "only description"}
        )
        assert response.status_code == 422

    def test_empty_body_returns_422(self):
        assert _req("post", self._url, json={}).status_code == 422

    def test_returns_500_on_service_error(self):
        with patch(
            "controllers.document_classify_controller.add_classification_type",
            new=AsyncMock(side_effect=Exception("Insert failed")),
        ):
            response = _req(
                "post", self._url, json={"classification_type": "NewType"}
            )
        assert response.status_code == 500
