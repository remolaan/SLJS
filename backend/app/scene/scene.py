from __future__ import annotations

from app.config import Settings, get_settings
from app.llm.base import Message
from app.llm.openrouter import OpenRouterProvider
from app.llm.stub import StubProvider
from app.models.schemas import TrialSnapshot

# Map an active speaker role to its display identity used by the scene agent.
SPEAKER_META = {
    "judge": {"name": "the Judge", "scene": "seated at the raised wooden bench, listening intently"},
    "prosecution": {"name": "the Prosecutor", "scene": "standing at the prosecution table presenting the case for the state"},
    "defense": {"name": "the Defense Counsel", "scene": "standing at the defense table responding on behalf of the accused"},
    "witness": {"name": "the Witness", "scene": "standing in the witness box giving testimony"},
    "intake": {"name": "the Court Clerk", "scene": "reading the case file and setting out the charges"},
}


def active_speaker(snapshot: TrialSnapshot) -> str:
    """Return the role of whoever last spoke (from the transcript tail)."""
    for turn in reversed(snapshot.transcript):
        if turn.role in ("judge", "prosecution", "defense", "witness", "intake"):
            return turn.role
    return "intake"


def scene_caption(snapshot: TrialSnapshot, settings: Settings | None = None) -> dict:
    """Use MiniMax M3 (free, via OpenRouter) to describe the current courtroom
    moment for the 2/3 scene panel.

    Falls back to a template caption when no OpenRouter key is configured.
    """
    settings = settings or get_settings()
    speaker = active_speaker(snapshot)
    meta = SPEAKER_META.get(speaker, SPEAKER_META["intake"])
    stage = snapshot.stage_label or "Case Intake"
    is_judgment = snapshot.status == "complete" and snapshot.judgment is not None

    prompt = (
        f"A courtroom simulation is at the stage '{stage}'. "
        f"Currently {meta['name']} is {meta['scene']}. "
        f"Case title: '{snapshot.case.title if snapshot.case else 'unknown'}'. "
        + ("The Judge has just delivered the verdict and is reading the judgment." if is_judgment else "")
        + (
            "Write ONE vivid, neutral third-person sentence (under 40 words) "
            "describing the visual scene as if narrating a documentary. "
            "No names of real people. Just the narration."
        )
    )

    if settings.openrouter_api_key:
        llm = OpenRouterProvider(settings)
        caption = llm.complete(
            [Message("system", "You write concise documentary-style narration for a courtroom simulation."),
             Message("user", prompt)],
            temperature=0.7,
        )
    else:
        caption = (
            f"{meta['name']} — {stage}. "
            f"({meta['scene']}.)"
        )

    return {
        "speaker": speaker,
        "speaker_name": meta["name"],
        "stage": stage,
        "caption": caption.strip(),
        "is_judgment": is_judgment,
        "model": settings.ui_model if settings.openrouter_api_key else "stub",
    }