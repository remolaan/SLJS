from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

from app.config import Settings, get_settings


class RunsStore:
    """JSON-file persistence for trials and evaluation runs.

    Satisfies the requirement that everything (transcripts, judgments,
    retrievals, evaluations) is saved for later review.
    """

    def __init__(self, settings: Settings):
        self.dir: Path = settings.runs_dir
        self.dir.mkdir(parents=True, exist_ok=True)

    def _path(self, kind: str, run_id: str) -> Path:
        return self.dir / f"{kind}_{run_id}.json"

    def save(self, kind: str, data: dict, run_id: str | None = None) -> str:
        run_id = run_id or f"{kind}_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        payload = {"run_id": run_id, "saved_at": time.time(), "data": data}
        self._path(kind, run_id).write_text(
            json.dumps(payload, default=str, indent=2), encoding="utf-8"
        )
        self._append_index(run_id, kind, data)
        return run_id

    def _append_index(self, run_id: str, kind: str, data: dict) -> None:
        idx_path = self.dir / "index.json"
        entries = []
        if idx_path.exists():
            try:
                entries = json.loads(idx_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                entries = []
        entries.append(
            {
                "run_id": run_id,
                "kind": kind,
                "title": data.get("case_title", ""),
                "saved_at": time.time(),
            }
        )
        idx_path.write_text(json.dumps(entries, indent=2), encoding="utf-8")

    def list_runs(self, kind: str | None = None) -> list[dict]:
        idx_path = self.dir / "index.json"
        if not idx_path.exists():
            return []
        try:
            entries = json.loads(idx_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []
        if kind:
            entries = [e for e in entries if e.get("kind") == kind]
        return list(reversed(entries))

    def load(self, kind: str, run_id: str) -> dict | None:
        path = self._path(kind, run_id)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None


_store: RunsStore | None = None


def get_runs_store(settings: Settings | None = None) -> RunsStore:
    global _store
    if _store is None:
        _store = RunsStore(settings or get_settings())
    return _store