from __future__ import annotations

import csv
import io
import json
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy import func
from sqlmodel import Session, select

from ..db import get_db
from ..models import (
    Event,
    ExerciseAttempt,
    FeedbackResponse,
    Participant,
    PracticeSession,
    Turn,
    TurnEvaluation,
)
from ..security import is_admin, sign_admin, verify_csrf
from ..services.ratelimit import enforce
from ..web import render

router = APIRouter(prefix="/admin")

ADMIN_COOKIE = "admin"
ADMIN_MAX_AGE = 8 * 3600


def _is_admin(request: Request) -> bool:
    return is_admin(request.app.state.admin_serializer, request.cookies.get(ADMIN_COOKIE))


def _csv(rows: list[list[object]], filename: str) -> Response:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerows(rows)
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _count(db: Session, statement) -> int:
    return int(db.exec(statement).one() or 0)


def _panel(request: Request, db: Session):
    counts = {
        "participants": _count(db, select(func.count(Participant.id))),
        "sessions": _count(db, select(func.count(PracticeSession.id))),
        "completed": _count(
            db,
            select(func.count(PracticeSession.id)).where(PracticeSession.completed == True),  # noqa: E712
        ),
        "turns": _count(db, select(func.count(Turn.id))),
        "evaluations": _count(db, select(func.count(TurnEvaluation.id))),
        "final_surveys": _count(
            db,
            select(func.count(FeedbackResponse.id)).where(FeedbackResponse.kind == "final"),
        ),
        "llm_errors": _count(
            db, select(func.count(Event.id)).where(Event.type == "llm_error")
        ),
    }
    errors = list(
        db.exec(
            select(Event)
            .where(Event.type.in_(["llm_error", "auth_failed"]))
            .order_by(Event.id.desc())
            .limit(8)
        ).all()
    )
    return render(
        request,
        "admin.html",
        participant=None,
        counts=counts,
        errors=errors,
    )


@router.get("")
def admin_home(request: Request, db: Session = Depends(get_db)):
    if not _is_admin(request):
        return render(request, "admin_login.html", participant=None, error=None)
    return _panel(request, db)


@router.post("/entrar")
def admin_login(
    request: Request,
    senha: str = Form(default=""),
    csrf_token: str = Form(default=""),
    db: Session = Depends(get_db),
):
    verify_csrf(request, csrf_token)
    enforce(request, "admin_login", 6)
    settings = request.app.state.settings

    if not settings.admin_password:
        return render(
            request,
            "admin_login.html",
            participant=None,
            error="Painel desativado: defina ADMIN_PASSWORD no ambiente.",
        )
    if not secrets.compare_digest(senha, settings.admin_password):
        db.add(
            Event(
                type="auth_failed",
                payload_json='{"area": "admin"}',
                created_at=datetime.now(timezone.utc),
            )
        )
        db.commit()
        return render(
            request,
            "admin_login.html",
            participant=None,
            error="Senha incorreta.",
        )

    response = RedirectResponse("/admin", status_code=303)
    response.set_cookie(
        ADMIN_COOKIE,
        sign_admin(request.app.state.admin_serializer),
        httponly=True,
        samesite="strict",
        max_age=ADMIN_MAX_AGE,
        secure=settings.cookie_secure,
    )
    return response


@router.post("/sair")
def admin_logout(request: Request, csrf_token: str = Form(default="")):
    verify_csrf(request, csrf_token)
    response = RedirectResponse("/admin", status_code=303)
    response.delete_cookie(ADMIN_COOKIE)
    return response


def _participants(db: Session) -> list[list[object]]:
    rows: list[list[object]] = [
        ["code", "age", "level", "languages", "interests", "consent_version", "consent_at", "created_at"]
    ]
    for item in db.exec(select(Participant).order_by(Participant.id)).all():
        rows.append(
            [
                item.code,
                item.age,
                item.level,
                item.languages,
                item.interests,
                item.consent_version,
                item.consent_at.isoformat() if item.consent_at else "",
                item.created_at.isoformat() if item.created_at else "",
            ]
        )
    return rows


def _sessions(db: Session) -> list[list[object]]:
    rows: list[list[object]] = [
        ["session_id", "participant_code", "lesson_id", "language", "mode", "started_at", "ended_at", "completed", "score"]
    ]
    query = (
        select(PracticeSession, Participant)
        .join(Participant, PracticeSession.participant_id == Participant.id)
        .order_by(PracticeSession.id)
    )
    for session, participant in db.exec(query).all():
        rows.append(
            [
                session.id,
                participant.code,
                session.lesson_id,
                session.language,
                session.mode,
                session.started_at.isoformat() if session.started_at else "",
                session.ended_at.isoformat() if session.ended_at else "",
                session.completed,
                session.score,
            ]
        )
    return rows


def _turns(db: Session) -> list[list[object]]:
    rows: list[list[object]] = [
        ["turn_id", "participant_code", "session_id", "role", "content", "created_at", "latency_ms", "model", "tokens_in", "tokens_out"]
    ]
    query = (
        select(Turn, PracticeSession, Participant)
        .join(PracticeSession, Turn.session_id == PracticeSession.id)
        .join(Participant, PracticeSession.participant_id == Participant.id)
        .order_by(Turn.id)
    )
    for turn, session, participant in db.exec(query).all():
        rows.append(
            [
                turn.id,
                participant.code,
                session.id,
                turn.role,
                turn.content,
                turn.created_at.isoformat() if turn.created_at else "",
                turn.latency_ms,
                turn.model,
                turn.tokens_in,
                turn.tokens_out,
            ]
        )
    return rows


def _evaluations(db: Session) -> list[list[object]]:
    rows: list[list[object]] = [
        ["evaluation_id", "participant_code", "session_id", "score", "errors_json", "feedback"]
    ]
    query = (
        select(TurnEvaluation, Turn, PracticeSession, Participant)
        .join(Turn, TurnEvaluation.turn_id == Turn.id)
        .join(PracticeSession, Turn.session_id == PracticeSession.id)
        .join(Participant, PracticeSession.participant_id == Participant.id)
        .order_by(TurnEvaluation.id)
    )
    for evaluation, turn, session, participant in db.exec(query).all():
        rows.append(
            [
                evaluation.id,
                participant.code,
                session.id,
                evaluation.score,
                evaluation.errors_json,
                evaluation.feedback,
            ]
        )
    return rows


def _feedback(db: Session) -> list[list[object]]:
    rows: list[list[object]] = [
        ["participant_code", "session_id", "kind", "instrument_version", "answers_json", "created_at"]
    ]
    query = (
        select(FeedbackResponse, Participant)
        .join(Participant, FeedbackResponse.participant_id == Participant.id)
        .order_by(FeedbackResponse.id)
    )
    for response, participant in db.exec(query).all():
        rows.append(
            [
                participant.code,
                response.session_id,
                response.kind,
                response.instrument_version,
                response.answers_json,
                response.created_at.isoformat() if response.created_at else "",
            ]
        )
    return rows


def _events(db: Session) -> list[list[object]]:
    rows: list[list[object]] = [
        ["participant_code", "type", "payload_json", "created_at"]
    ]
    query = (
        select(Event, Participant)
        .join(Participant, Event.participant_id == Participant.id, isouter=True)
        .order_by(Event.id)
    )
    for event, participant in db.exec(query).all():
        rows.append(
            [
                participant.code if participant else "",
                event.type,
                event.payload_json,
                event.created_at.isoformat() if event.created_at else "",
            ]
        )
    return rows


def _exercises(db: Session) -> list[list[object]]:
    rows: list[list[object]] = [
        [
            "participant_code",
            "session_id",
            "lesson_id",
            "language",
            "exercise_index",
            "chosen",
            "correct",
            "created_at",
        ]
    ]
    query = (
        select(ExerciseAttempt, Participant)
        .join(Participant, ExerciseAttempt.participant_id == Participant.id)
        .order_by(ExerciseAttempt.id)
    )
    for attempt, participant in db.exec(query).all():
        rows.append(
            [
                participant.code,
                attempt.session_id,
                attempt.lesson_id,
                attempt.language,
                attempt.exercise_index,
                attempt.chosen,
                attempt.correct,
                attempt.created_at.isoformat() if attempt.created_at else "",
            ]
        )
    return rows


EXPORTS = {
    "participantes": (_participants, "participantes.csv"),
    "sessoes": (_sessions, "sessoes.csv"),
    "turnos": (_turns, "turnos.csv"),
    "avaliacoes": (_evaluations, "avaliacoes.csv"),
    "exercicios": (_exercises, "exercicios.csv"),
    "questionarios": (_feedback, "questionarios.csv"),
    "eventos": (_events, "eventos.csv"),
}


@router.get("/exportar/{kind}")
def admin_export(kind: str, request: Request, db: Session = Depends(get_db)):
    if not _is_admin(request):
        return RedirectResponse("/admin", status_code=303)
    if kind not in EXPORTS:
        return Response(status_code=404)
    builder, filename = EXPORTS[kind]
    db.add(
        Event(
            type="admin_export",
            payload_json=json.dumps({"kind": kind}),
            created_at=datetime.now(timezone.utc),
        )
    )
    db.commit()
    return _csv(builder(db), filename)
