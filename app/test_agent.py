"""
Direct agent test — calls DocumentClassifyAgent.arun() without the HTTP layer.

Required env vars:
  OPENAI_API_KEY             – Moonshot API key
  POSTGRES_CONNECTION_STRING – asyncpg-compatible Postgres URL
                               e.g. postgresql://postgres:admin123@localhost:5432/AgentHub
"""

import asyncio
import os
import sys
from pathlib import Path

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import pytest

from src.utils.pdf_utils import pdf_to_base64_images
from dotenv import load_dotenv

load_dotenv()

pytestmark = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY") or not os.getenv("POSTGRES_CONNECTION_STRING"),
    reason="OPENAI_API_KEY and POSTGRES_CONNECTION_STRING are both required",
)

_PDF_NAME = "66B9FFF2-39CB-437E-A923-0A8EECBC757C-463242-IF.pdf"
_PDF_PATH = Path(__file__).parent.parent / "documents_need_classify" / _PDF_NAME
_PDF_IMAGES = pdf_to_base64_images(_PDF_PATH, dpi=150)

_loop = asyncio.new_event_loop()


@pytest.fixture(scope="module")
def agent():
    from src.infrastructure.postgres_db import init_pool, close_pool
    from src.agents.document_classify_agent.agent import DocumentClassifyAgent

    async def _startup():
        await init_pool()
        return DocumentClassifyAgent()

    instance = _loop.run_until_complete(_startup())
    yield instance
    _loop.run_until_complete(close_pool())
    _loop.close()


@pytest.fixture(scope="module")
def agent_result(agent):
    from langgraph.errors import GraphInterrupt

    async def _run():
        try:
            result = await agent.arun(_PDF_NAME, _PDF_IMAGES)
            return {"status": "completed", "data": result}
        except GraphInterrupt as exc:
            return {"status": "interrupted", "interrupt": exc.args[0] if exc.args else {}}

    return _loop.run_until_complete(_run())


class TestAgentDirect:
    def test_returns_dict(self, agent_result):
        assert isinstance(agent_result, dict)
        assert agent_result["status"] in ("completed", "interrupted")

    # ── completed (auto-classified) path ────────────────────────────────────
    def test_completed_has_required_fields(self, agent_result):
        if agent_result["status"] != "completed":
            pytest.skip("Agent interrupted — skipping completed-only assertions")
        data = agent_result["data"]
        for field in ("classification_type", "confidence_score", "reasoning"):
            assert field in data, f"Missing field: {field}"

    def test_classification_type_nonempty(self, agent_result):
        if agent_result["status"] != "completed":
            pytest.skip("Agent interrupted")
        assert isinstance(agent_result["data"]["classification_type"], str)
        assert agent_result["data"]["classification_type"].strip()

    def test_confidence_score_in_range(self, agent_result):
        if agent_result["status"] != "completed":
            pytest.skip("Agent interrupted")
        score = agent_result["data"]["confidence_score"]
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_reasoning_nonempty(self, agent_result):
        if agent_result["status"] != "completed":
            pytest.skip("Agent interrupted")
        assert isinstance(agent_result["data"]["reasoning"], str)
        assert agent_result["data"]["reasoning"].strip()

    # ── interrupted (awaiting human) path ───────────────────────────────────
    def test_interrupted_has_interrupt_payload(self, agent_result):
        if agent_result["status"] != "interrupted":
            pytest.skip("Agent completed without interrupt")
        interrupt = agent_result["interrupt"]
        assert isinstance(interrupt, (dict, list))


@pytest.fixture(scope="module")
def resume_result(agent, agent_result):
    """Resume the interrupted graph with a human approval. Skipped if no interrupt."""
    from src.models.document_human_response_model import DocumentHumanResponseModel
    from langgraph.errors import GraphInterrupt

    if agent_result["status"] != "interrupted":
        pytest.skip("No interrupt to resume")

    human_response = DocumentHumanResponseModel(
        document_name=_PDF_NAME,
        human_approved=True,
        human_correction="",
        agent_classification_type="",
    )

    async def _run():
        try:
            await agent.aresume(_PDF_NAME, human_response)
            return {"status": "completed"}
        except GraphInterrupt as exc:
            return {"status": "interrupted", "interrupt": exc.args[0] if exc.args else {}}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    return _loop.run_until_complete(_run())


class TestAgentResume:
    def test_resume_completes(self, resume_result):
        assert resume_result["status"] in ("completed", "interrupted"), (
            f"aresume raised an error: {resume_result.get('error')}"
        )

    def test_resume_no_error(self, resume_result):
        assert resume_result["status"] != "error", resume_result.get("error")
