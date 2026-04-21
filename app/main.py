# FastAPI app — tool API only; Twilio and ElevenLabs configured on their dashboards
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from src.infrastructure.postgres_db import init_pool, close_pool
from controllers.document_classify_controller import router as document_classify_router
from src.agents.document_classify_agent.agent import DocumentClassifyAgent

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: init DB and Redis. Shutdown: close both."""
    await init_pool()
    app.state.agents = {
        "document_classify_agent": DocumentClassifyAgent()
    }
    yield
    await close_pool()


app = FastAPI(
    title="Agent Hub — Tools API",
    description="Centralized API for all agents.",
    lifespan=lifespan,
)

app.include_router(document_classify_router)


@app.get("/")
async def root():
    return {"service": "agent-hub", "docs": "/docs"}