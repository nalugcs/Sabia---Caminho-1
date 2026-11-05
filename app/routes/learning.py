from __future__ import annotations

import json
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from ..db import get_db
from ..deps import current_participant
from ..models import (
    Event,
    ExerciseAttempt,
    FeedbackResponse,
    LessonProgress,
    Participant,
    PracticeSession,
    Turn,
    TurnEvaluation,
)
from ..services.exercises import build_exercise_view
from ..services.llm import LLMError
from ..services.instrument import FINAL_BLOCKS, LIKERT_KEYS, OPEN_QUESTIONS
from ..services.markdown_render import render_markdown
from ..services.parsing import parse_json_object
from ..services.personalization import recommend
from ..services.prompts import feedback_messages, turn_messages
from ..services.ratelimit import enforce
from ..security import verify_csrf
from ..web import render

router = APIRouter()


class TurnIn(BaseModel):
    session_id: int
    message: str = Field(min_length=1, max_length=2000)


class FinishIn(BaseModel):
    session_id: int


class MicroIn(BaseModel):
    session_id: int
    answers: dict[str, int]


class ExerciseIn(BaseModel):
    session_id: int
    exercise_index: int = Field(ge=0, le=19)
    choice: str = Field(min_length=1, max_length=300)


def _participant_or_redirect(request: Request, db: Session):
    participant = current_participant(request, db)
    if participant is None:
        return None, RedirectResponse("/", status_code=303)
    return participant, None


def _history(db: Session, session_id: int) -> list[Turn]:
    return list(
        db.exec(select(Turn).where(Turn.session_id == session_id).order_by(Turn.id)).all()
    )


def _completed_count(db: Session, participant_id: int) -> int:
    return len(
        db.exec(
            select(PracticeSession.id).where(
                PracticeSession.participant_id == participant_id,
                PracticeSession.completed == True,  # noqa: E712
            )
        ).all()
    )


@router.get("/app")
def dashboard(request: Request, db: Session = Depends(get_db)):
    participant, redirect = _participant_or_redirect(request, db)
    if redirect:
        return redirect
    settings = request.app.state.settings

    completed = list(
        db.exec(
            select(PracticeSession).where(
                PracticeSession.participant_id == participant.id,
                PracticeSession.completed == True,  # noqa: E712
            )
        ).all()
    )
    final = db.exec(
        select(FeedbackResponse).where(
            FeedbackResponse.participant_id == participant.id,
            FeedbackResponse.kind == "final",
        )
    ).first()
    catalog = request.app.state.catalog
    recommendation = recommend(catalog, participant, db)
    return render(
        request,
        "dashboard.html",
        participant=participant,
        recommendation=recommendation,
        done=len(completed),
        required=settings.required_sessions,
        sessions=completed[-3:],
        final_answered=final is not None,
        needs_final=len(completed) >= settings.required_sessions and final is None,
        questionario_ok=request.query_params.get("questionario") == "ok",
    )


@router.get("/licao/{language}/{lesson_id}")
def lesson_page(
    request: Request, language: str, lesson_id: int, db: Session = Depends(get_db)
):
    participant, redirect = _participant_or_redirect(request, db)
    if redirect:
        return redirect

    catalog = request.app.state.catalog
    lesson = catalog.get(language, lesson_id)
    if lesson is None:
        raise HTTPException(404, "Lição não encontrada.")

    session = db.exec(
        select(PracticeSession)
        .where(
            PracticeSession.participant_id == participant.id,
            PracticeSession.language == language,
            PracticeSession.lesson_id == lesson_id,
            PracticeSession.completed == False,  # noqa: E712
        )
        .order_by(PracticeSession.id.desc())
    ).first()

    if session is None:
        session = PracticeSession(
            participant_id=participant.id,
            lesson_id=lesson_id,
            language=language,
            mode="conversa",
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        opening = (
            f"Vamos praticar {lesson['theme']} ({lesson['level']}).\n\n"
            f"{lesson['objective']}\n\n"
            f"Comece com uma frase parecida com: “{lesson['phrases'][0]['target']}”"
        )
        db.add(Turn(session_id=session.id, role="assistant", content=opening))
        db.commit()

    turns = _history(db, session.id)
    language_name = (catalog.get_language(language) or {}).get("language", language)
    exercises = build_exercise_view(lesson, seed=session.id * 1000 + lesson_id)
    return render(
        request,
        "lesson.html",
        participant=participant,
        lesson=lesson,
        language_code=language,
        language_name=language_name,
        session=session,
        turns=turns,
        exercises=exercises,
    )


@router.post("/api/turno")
async def api_turn(
    request: Request, payload: TurnIn, db: Session = Depends(get_db)
):
    verify_csrf(request, request.headers.get("x-csrf-token"))
    enforce(request, "turn", 40)
    participant = current_participant(request, db)
    if participant is None:
        raise HTTPException(401, "Sessão expirada. Entre novamente.")

    session = db.get(PracticeSession, payload.session_id)
    if session is None or session.participant_id != participant.id:
        raise HTTPException(404, "Sessão de lição não encontrada.")
    if session.completed:
        raise HTTPException(409, "Esta lição já foi encerrada.")

    catalog = request.app.state.catalog
    lesson = catalog.get(session.language, session.lesson_id)
    if lesson is None:
        raise HTTPException(500, "Conteúdo da lição indisponível.")

    history = [
        {"role": turn.role, "content": turn.content}
        for turn in _history(db, session.id)
        if turn.role in {"user", "assistant"}
    ]
    messages, meta = turn_messages(
        lesson,
        (catalog.get_language(session.language) or {}).get("language", session.language),
        session.mode,
        history,
        payload.message,
    )

    settings = request.app.state.settings
    started = time.monotonic()
    try:
        response = await request.app.state.llm.complete(
            messages,
            model=settings.llm_model,
            temperature=0.4,
            max_tokens=600,
            meta=meta,
        )
    except LLMError as exc:
        db.add(
            Event(
                participant_id=participant.id,
                type="llm_error",
                payload_json=json.dumps({"error": str(exc)[:300]}),
            )
        )
        db.commit()
        raise HTTPException(
            502, "O modelo não respondeu agora. Tente enviar de novo em instantes."
        ) from exc

    data = parse_json_object(response.text) or {}
    reply = str(data.get("resposta") or response.text or "").strip()
    if not reply:
        reply = "Não consegui formular a resposta. Tente outra frase."

    score = data.get("nota")
    try:
        score = max(0, min(10, int(score))) if score is not None else None
    except (TypeError, ValueError):
        score = None

    db.add(Turn(session_id=session.id, role="user", content=payload.message))
    db.commit()

    assistant = Turn(
        session_id=session.id,
        role="assistant",
        content=reply,
        latency_ms=response.latency_ms or int((time.monotonic() - started) * 1000),
        model=response.model or settings.llm_model,
        tokens_in=response.prompt_tokens,
        tokens_out=response.completion_tokens,
    )
    db.add(assistant)
    db.commit()
    db.refresh(assistant)

    errors = data.get("erros") if isinstance(data.get("erros"), list) else []
    evaluation = TurnEvaluation(
        turn_id=assistant.id,
        score=score,
        errors_json=json.dumps(errors, ensure_ascii=False),
        feedback=str(data.get("explicacao") or data.get("correcao") or "")[:2000],
    )
    db.add(evaluation)
    if score is not None:
        session.score = float(score)
    db.add(session)
    db.add(
        Event(
            participant_id=participant.id,
            type="turn",
            payload_json=json.dumps(
                {
                    "session_id": session.id,
                    "lesson_id": session.lesson_id,
                    "score": score,
                    "latency_ms": assistant.latency_ms,
                }
            ),
        )
    )
    db.commit()

    return {
        "ok": True,
        "session_id": session.id,
        "score": score,
        "resposta": reply,
        "correcao": data.get("correcao") or "",
        "explicacao": data.get("explicacao") or "",
        "exemplo": data.get("exemplo") or "",
        "proximo_passo": data.get("proximo_passo") or "",
        "erros": errors,
    }


@router.post("/api/encerrar")
async def api_finish(
    request: Request, payload: FinishIn, db: Session = Depends(get_db)
):
    verify_csrf(request, request.headers.get("x-csrf-token"))
    enforce(request, "finish", 20)
    participant = current_participant(request, db)
    if participant is None:
        raise HTTPException(401, "Sessão expirada. Entre novamente.")

    session = db.get(PracticeSession, payload.session_id)
    if session is None or session.participant_id != participant.id:
        raise HTTPException(404, "Sessão de lição não encontrada.")

    turns = _history(db, session.id)
    evaluations = list(
        db.exec(
            select(TurnEvaluation)
            .join(Turn, TurnEvaluation.turn_id == Turn.id)
            .where(Turn.session_id == session.id)
        ).all()
    )
    scores = [item.score for item in evaluations if item.score is not None]
    average = round(sum(scores) / len(scores), 1) if scores else None

    catalog = request.app.state.catalog
    lesson = catalog.get(session.language, session.lesson_id) or {}
    history = [{"role": turn.role, "content": turn.content} for turn in turns]
    messages, meta = feedback_messages(
        lesson,
        (catalog.get_language(session.language) or {}).get("language", session.language),
        session.mode,
        history,
        average,
    )
    settings = request.app.state.settings
    try:
        response = await request.app.state.llm.complete(
            messages,
            model=settings.llm_model,
            temperature=0.3,
            max_tokens=700,
            meta=meta,
        )
        feedback_text = response.text.strip()
    except LLMError:
        feedback_text = (
            "## Resumo\nA aula foi encerrada, mas o feedback automático não respondeu.\n\n"
            f"## Nota final\n{average if average is not None else '—'}/10\n\n"
            "## Próximo passo\nTente novamente mais tarde."
        )

    session.completed = True
    session.ended_at = datetime.now(timezone.utc)
    session.score = average
    session.feedback_text = feedback_text
    db.add(session)

    progress = db.exec(
        select(LessonProgress).where(
            LessonProgress.participant_id == participant.id,
            LessonProgress.lesson_id == session.lesson_id,
            LessonProgress.language == session.language,
        )
    ).first()
    if progress is None:
        progress = LessonProgress(
            participant_id=participant.id,
            lesson_id=session.lesson_id,
            language=session.language,
        )
    progress.status = "concluida"
    progress.attempts += 1
    if average is not None:
        progress.best_score = max(progress.best_score or 0, average)
    db.add(progress)
    db.add(
        Event(
            participant_id=participant.id,
            type="lesson_finished",
            payload_json=json.dumps(
                {"session_id": session.id, "score": average, "lesson_id": session.lesson_id}
            ),
        )
    )
    db.commit()

    return {"ok": True, "session_id": session.id, "score": average}


@router.get("/feedback/{session_id}")
def feedback_page(
    request: Request, session_id: int, db: Session = Depends(get_db)
):
    participant, redirect = _participant_or_redirect(request, db)
    if redirect:
        return redirect
    session = db.get(PracticeSession, session_id)
    if session is None or session.participant_id != participant.id:
        raise HTTPException(404, "Sessão não encontrada.")
    answered = db.exec(
        select(FeedbackResponse).where(
            FeedbackResponse.participant_id == participant.id,
            FeedbackResponse.session_id == session_id,
            FeedbackResponse.kind == "micro",
        )
    ).all()
    return render(
        request,
        "feedback.html",
        participant=participant,
        session=session,
        answered=bool(answered),
        feedback_html=render_markdown(session.feedback_text),
        language_name=(request.app.state.catalog.get_language(session.language) or {}).get(
            "language", session.language
        ),
    )


@router.post("/api/micro")
def api_micro(
    request: Request, payload: MicroIn, db: Session = Depends(get_db)
):
    verify_csrf(request, request.headers.get("x-csrf-token"))
    enforce(request, "micro", 20)
    participant = current_participant(request, db)
    if participant is None:
        raise HTTPException(401, "Sessão expirada. Entre novamente.")
    session = db.get(PracticeSession, payload.session_id)
    if session is None or session.participant_id != participant.id:
        raise HTTPException(404, "Sessão não encontrada.")

    clean = {}
    for key, value in payload.answers.items():
        try:
            number = int(value)
        except (TypeError, ValueError):
            continue
        if 1 <= number <= 5:
            clean[str(key)] = number
    if not clean:
        raise HTTPException(400, "Responda pelo menos um item.")

    db.add(
        FeedbackResponse(
            participant_id=participant.id,
            session_id=session.id,
            kind="micro",
            instrument_version=request.app.state.settings.instrument_version,
            answers_json=json.dumps(
                {"session_id": session.id, "answers": clean}, ensure_ascii=False
            ),
        )
    )
    db.add(
        Event(
            participant_id=participant.id,
            type="micro_survey",
            payload_json=json.dumps({"session_id": session.id, "answers": clean}),
        )
    )
    db.commit()
    return {"ok": True}


@router.post("/api/exercicio")
def api_exercise(
    request: Request, payload: ExerciseIn, db: Session = Depends(get_db)
):
    verify_csrf(request, request.headers.get("x-csrf-token"))
    enforce(request, "exercise", 60)
    participant = current_participant(request, db)
    if participant is None:
        raise HTTPException(401, "Sessão expirada. Entre novamente.")

    session = db.get(PracticeSession, payload.session_id)
    if session is None or session.participant_id != participant.id:
        raise HTTPException(404, "Sessão de lição não encontrada.")

    lesson = request.app.state.catalog.get(session.language, session.lesson_id)
    if lesson is None:
        raise HTTPException(500, "Conteúdo da lição indisponível.")
    exercises = lesson.get("exercises", [])
    if not 0 <= payload.exercise_index < len(exercises):
        raise HTTPException(400, "Exercício inválido.")
    exercise = exercises[payload.exercise_index]
    if payload.choice not in exercise.get("options", []):
        raise HTTPException(400, "Alternativa inválida.")

    correct = payload.choice == exercise.get("answer")
    attempt = db.exec(
        select(ExerciseAttempt).where(
            ExerciseAttempt.participant_id == participant.id,
            ExerciseAttempt.session_id == session.id,
            ExerciseAttempt.exercise_index == payload.exercise_index,
        )
    ).first()
    if attempt is None:
        attempt = ExerciseAttempt(
            participant_id=participant.id,
            session_id=session.id,
            lesson_id=session.lesson_id,
            language=session.language,
            exercise_index=payload.exercise_index,
            chosen=payload.choice,
            correct=correct,
        )
    else:
        attempt.chosen = payload.choice
        attempt.correct = correct
        attempt.created_at = datetime.now(timezone.utc)
    db.add(attempt)
    db.add(
        Event(
            participant_id=participant.id,
            type="exercise",
            payload_json=json.dumps(
                {
                    "session_id": session.id,
                    "lesson_id": session.lesson_id,
                    "exercise_index": payload.exercise_index,
                    "correct": correct,
                }
            ),
        )
    )
    db.commit()
    return {
        "ok": True,
        "correct": correct,
        "answer": exercise.get("answer", ""),
        "explanation": exercise.get("explanation", ""),
    }


@router.get("/questionario")
def questionnaire_page(request: Request, db: Session = Depends(get_db)):
    participant, redirect = _participant_or_redirect(request, db)
    if redirect:
        return redirect
    settings = request.app.state.settings
    done = _completed_count(db, participant.id)
    final = db.exec(
        select(FeedbackResponse).where(
            FeedbackResponse.participant_id == participant.id,
            FeedbackResponse.kind == "final",
        )
    ).first()
    return render(
        request,
        "questionario.html",
        participant=participant,
        blocks=FINAL_BLOCKS,
        open_questions=OPEN_QUESTIONS,
        done=done,
        required=settings.required_sessions,
        answered=final is not None,
        blocked=done < settings.required_sessions,
        error=None,
    )


@router.post("/questionario")
async def questionnaire_submit(request: Request, db: Session = Depends(get_db)):
    participant = current_participant(request, db)
    if participant is None:
        return RedirectResponse("/", status_code=303)

    form = await request.form()
    verify_csrf(request, str(form.get("csrf_token") or ""))
    enforce(request, "final_survey", 5)

    settings = request.app.state.settings
    done = _completed_count(db, participant.id)
    if done < settings.required_sessions:
        return render(
            request,
            "questionario.html",
            participant=participant,
            blocks=FINAL_BLOCKS,
            open_questions=OPEN_QUESTIONS,
            done=done,
            required=settings.required_sessions,
            answered=False,
            blocked=True,
            error=None,
        )

    answers: dict[str, object] = {}
    missing: list[str] = []
    for key in LIKERT_KEYS:
        try:
            value = int(str(form.get(key) or ""))
        except (TypeError, ValueError):
            missing.append(key)
            continue
        if not 1 <= value <= 5:
            missing.append(key)
            continue
        answers[key] = value

    try:
        nps = int(str(form.get("nps") or ""))
        if not 0 <= nps <= 10:
            raise ValueError
    except (TypeError, ValueError):
        missing.append("nps")
        nps = None
    if nps is not None:
        answers["nps"] = nps

    if missing:
        return render(
            request,
            "questionario.html",
            participant=participant,
            blocks=FINAL_BLOCKS,
            open_questions=OPEN_QUESTIONS,
            done=done,
            required=settings.required_sessions,
            answered=False,
            blocked=False,
            error=f"Faltam {len(missing)} item(ns). Responda todos para enviar.",
        )

    for key, _ in OPEN_QUESTIONS:
        answers[key] = str(form.get(key) or "").strip()[:2000]

    existing = db.exec(
        select(FeedbackResponse).where(
            FeedbackResponse.participant_id == participant.id,
            FeedbackResponse.kind == "final",
        )
    ).first()
    payload = json.dumps(answers, ensure_ascii=False)
    if existing:
        existing.answers_json = payload
        existing.instrument_version = settings.instrument_version
        existing.created_at = datetime.now(timezone.utc)
        db.add(existing)
    else:
        db.add(
            FeedbackResponse(
                participant_id=participant.id,
                kind="final",
                instrument_version=settings.instrument_version,
                answers_json=payload,
            )
        )
    db.add(
        Event(
            participant_id=participant.id,
            type="final_survey",
            payload_json=json.dumps({"items": len(answers)}),
        )
    )
    db.commit()
    return RedirectResponse("/app?questionario=ok", status_code=303)
