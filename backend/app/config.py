from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Runtime configuration, read from env / backend/.env."""

    model_config = SettingsConfigDict(
        env_file=(
            BACKEND_DIR / ".env",
            Path(__file__).resolve().parent.parent.parent / ".env",  # repo root .env
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- LLM ---
    llm_provider: str = Field(default="deepseek")  # "deepseek" | "openrouter" | "minimax" | "stub"
    deepseek_api_key: str = Field(default="")
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    deepseek_temperature: float = 0.4

    # --- UI/design helper (OpenRouter, e.g. MiniMax M3 free) ---
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    ui_model: str = "minimax/minimax-m3:free"
    ui_provider: str = "openrouter"

    # --- Developer / coding helper model (free OpenRouter) ---
    dev_model: str = "minimax/minimax-m3:free"

    # Free models to rotate across for agents / image / scene generation so a
    # single model's 50/day free cap doesn't break the UI. Kept in order of
    # preference; capable general text models come first.
    free_models: list[str] = [
        "minimax/minimax-m3:free",
        "google/gemma-4-31b-it:free",
        "google/gemma-4-26b-a4b-it:free",
        "z-ai/glm-5.2:free",
        "cohere/north-mini-code:free",
        "nvidia/nemotron-3-super-120b-a12b:free",
        "nvidia/nemotron-3-ultra-550b-a55b:free",
        "nvidia/nemotron-3.5-lightning:free",
        "minimax/minimax-m2.7:free",
        "thinkingmachines/inkling:free",
        "poolside/laguna-s-2.1:free",
        "liquid/lfm-2.5-2.6b:free",
    ]

    # --- RAG ---
    embedding_model: str = "BAAI/bge-m3"
    chroma_persist_dir: Path = BACKEND_DIR / "data" / "vectorstore"
    corpus_dir: Path = BACKEND_DIR / "data" / "corpus"
    runs_dir: Path = BACKEND_DIR / "data" / "runs"
    rag_top_k_statutes: int = 6
    rag_top_k_precedent: int = 5
    rag_enabled: bool = True

    # --- Image generation (FREE: MiniMax M3 -> SVG) ---
    image_model: str = "minimax/minimax-m3:free"
    image_enabled: bool = True
    image_cache_dir: Path = BACKEND_DIR / "data" / "image_cache"

    # --- App ---
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    @field_validator("chroma_persist_dir", "corpus_dir", "runs_dir", "image_cache_dir", mode="before")
    @classmethod
    def _resolve_path(cls, v):
        p = Path(v)
        if not p.is_absolute():
            p = BACKEND_DIR / p
        return p

    @property
    def effective_provider(self) -> str:
        """Pick the working provider: DeepSeek, else free OpenRouter, else stub.

        This lets the trial agents (prosecution/defense/judge/intake) run on
        free OpenRouter models whenever an OpenRouter key is present, instead
        of falling back to the offline stub.
        """
        if self.llm_provider == "deepseek" and self.deepseek_api_key:
            return "deepseek"
        if self.openrouter_api_key:
            return "openrouter"
        return "stub"


@lru_cache
def get_settings() -> Settings:
    return Settings()