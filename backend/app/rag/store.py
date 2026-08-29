from __future__ import annotations

import hashlib
import logging

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import Settings, get_settings
from app.rag.chunking import Chunk, load_corpus

logger = logging.getLogger(__name__)

COLLECTION_NAME = "sri_lankan_law"


def _id_for(chunk: Chunk) -> str:
    return hashlib.sha1(chunk.chunk_id.encode("utf-8")).hexdigest()[:24]


class VectorStore:
    """Chroma-backed store for statute + precedent chunks."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._client = chromadb.PersistentClient(
            path=str(settings.chroma_persist_dir),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    # --- ingestion ---------------------------------------------------------
    def ingest(self, chunks: list[Chunk], force: bool = False) -> int:
        """Add chunks to the store. Returns number newly added."""
        existing = set(self._collection.get(include=[])["ids"])
        to_add = [c for c in chunks if _id_for(c) not in existing]
        if force:
            to_add = chunks

        if not to_add:
            logger.info("Vector store up to date (%d chunks).", len(existing))
            return 0

        ids = [_id_for(c) for c in to_add]
        docs = [c.text for c in to_add]
        metas = [c.as_dict() for c in to_add]

        # Add in batches to avoid huge single requests.
        batch = 64
        for i in range(0, len(ids), batch):
            self._collection.add(
                ids=ids[i : i + batch],
                documents=docs[i : i + batch],
                metadatas=metas[i : i + batch],
            )
        logger.info("Ingested %d chunks.", len(to_add))
        return len(to_add)

    def sync_corpus(self, force: bool = False) -> int:
        chunks = load_corpus(self.settings.corpus_dir)
        if not chunks:
            logger.warning("No corpus files found in %s", self.settings.corpus_dir)
        return self.ingest(chunks, force=force)

    # --- retrieval ---------------------------------------------------------
    def query(self, text: str, n_results: int = 5, doc_type: str | None = None):
        where = {"doc_type": doc_type} if doc_type else None
        res = self._collection.query(
            query_texts=[text],
            n_results=n_results,
            where=where,
        )
        results = []
        ids = res.get("ids", [[]])[0]
        docs = res.get("documents", [[]])[0]
        dists = res.get("distances", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        for i, doc_id in enumerate(ids):
            meta = metas[i] or {}
            results.append(
                {
                    "chunk_id": doc_id,
                    "doc_type": meta.get("doc_type", ""),
                    "source": meta.get("source", ""),
                    "cite": meta.get("cite", ""),
                    "text": docs[i],
                    "relevance": round(1.0 - dists[i], 4) if dists else 0.0,
                }
            )
        return results

    def count(self) -> int:
        return self._collection.count()


def get_vectorstore(settings: Settings | None = None) -> VectorStore:
    return VectorStore(settings or get_settings())