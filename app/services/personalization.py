from __future__ import annotations

import json
import logging
from collections import Counter

from fastapi import HTTPException
from sqlmodel import Session, select

from ..models import LessonProgress, Participant, PracticeSession, Turn, TurnEvaluation
from .lessons import LessonCatalog

logger = logging.getLogger(__name__)

LEVEL_BAND = {
    "iniciante": 1,
    "básico": 1,
    "basico": 1,
    "intermediário": 2,
    "intermediario": 2,
    "avançado": 3,
    "avancado": 3,
    "fluente": 4,
}


def level_band(level: str) -> int:
    return LEVEL_BAND.get((level or "").strip().lower(), 1)


def interests_of(participant: Participant) -> list[str]:
    try:
        data = json.loads(participant.interests or "[]")
    except json.JSONDecodeError:
        data = []
    return [str(item) for item in data] if isinstance(data, list) else []


def language_of(participant: Participant) -> str:
    try:
        data = json.loads(participant.languages or "[]")
    except json.JSONDecodeError:
        data = []
    if isinstance(data, list) and data:
        return data[0]
    return "en"


ERROR_LABELS = {
    "gramatica": "gramática",
    "vocabulario": "vocabulário",
    "ortografia": "ortografia",
    "fluencia": "fluência",
}


def top_error(participant: Participant, db: Session) -> dict | None:
    """Erro mais recorrente do participante, aprendido dos turnos anteriores."""

    rows = db.exec(
        select(TurnEvaluation.errors_json)
        .join(Turn, TurnEvaluation.turn_id == Turn.id)
        .join(PracticeSession, Turn.session_id == PracticeSession.id)
        .where(PracticeSession.participant_id == participant.id)
    ).all()
    counts: Counter[str] = Counter()
    for raw in rows:
        try:
            items = json.loads(raw or "[]")
        except (TypeError, json.JSONDecodeError):
            continue
        if not isinstance(items, list):
            continue
        for item in items:
            if isinstance(item, dict) and item.get("tipo"):
                counts[str(item["tipo"])] += 1
    if not counts:
        return None
    tipo, count = counts.most_common(1)[0]
    return {"tipo": tipo, "label": ERROR_LABELS.get(tipo, tipo), "count": count}


def recommend(catalog: LessonCatalog, participant: Participant, db: Session) -> dict:
    """Recomendação v1: nível, interesse, erro recorrente e novidade."""

    code = language_of(participant)
    language = catalog.get_language(code)
    if language is None:
        code = "en"
        language = catalog.get_language(code)
    if language is None:  # pragma: no cover - catálogo sempre tem en
        raise HTTPException(500, "catálogo de lições vazio")

    completed = set(
        db.exec(
            select(LessonProgress.lesson_id).where(
                LessonProgress.participant_id == participant.id,
                LessonProgress.language == code,
                LessonProgress.status == "concluida",
            )
        ).all()
    )
    band = level_band(participant.level)
    lessons = language["lessons"]
    interests = [i.lower() for i in interests_of(participant)]
    recurring = top_error(participant, db)

    def score(lesson: dict) -> tuple[int, int]:
        theme = lesson["theme"].lower()
        interest_hit = int(any(tag and tag in theme for tag in interests))
        same_band = int(level_band(lesson["level"]) == band)
        novelty = 1 if lesson["id"] not in completed else 0
        review_hit = int(bool(recurring) and "revis" in theme)
        return (same_band * 2 + interest_hit * 2 + novelty + review_hit, -lesson["id"])

    candidates = [lesson for lesson in lessons if lesson["id"] not in completed]
    if not candidates:
        candidates = lessons

    chosen = max(candidates, key=score)
    reasons = []
    if level_band(chosen["level"]) == band:
        reasons.append("está no seu nível")
    if any(tag and tag in chosen["theme"].lower() for tag in interests):
        reasons.append("combina com seus interesses")
    if recurring and "revis" in chosen["theme"].lower():
        reasons.append(f"revisa seu erro recorrente de {recurring['label']}")
    reasons.append("é uma lição nova")
    return {
        "language_code": code,
        "language": language["language"],
        "lesson": chosen,
        "reason": ", ".join(reasons),
        "top_error": recurring,
    }
