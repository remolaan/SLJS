from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title="AI Judge — Courtroom Simulation for Sri Lanka",
    version="0.1.0",
    description=(
        "Research/education simulation only. Multi-agent LangGraph pipeline "
        "(intake → prosecution → defense → witness → closings → judge with RAG) "
        "that produces a structured, citation-anchored judgment."
    ),
)

app.include_router(router)

# Serve pre-generated images as static files so they load instantly.
app.mount(
    "/static/images",
    StaticFiles(directory=str(settings.image_cache_dir)),
    name="images",
)


@app.get("/health")
def health() -> dict:
    from app.llm import get_llm

    return {
        "status": "ok",
        "llm_provider": get_llm(settings).name,
        "rag_enabled": settings.rag_enabled,
    }