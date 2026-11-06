from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlmodel import Session, select

from ..db import get_db
from ..deps import current_participant
from ..models import Event, Participant
from ..security import generate_code, sign_code, verify_csrf
from ..services.ratelimit import enforce
from ..web import render

router = APIRouter()

LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]
LEVEL_LABELS = {
    "A1": "A1 — Iniciante",
    "A2": "A2 — Básico",
    "B1": "B1 — Intermediário",
    "B2": "B2 — Intermediário superior",
    "C1": "C1 — Avançado",
    "C2": "C2 — Proficiência",
}
LEVEL_OPTIONS = [(code, LEVEL_LABELS[code]) for code in LEVELS]
# compatibilidade com cadastros antigos
ALLOWED_LEVELS = set(LEVELS) | {
    "iniciante", "básico", "basico", "intermediário", "intermediario",
    "avançado", "avancado", "fluente",
}
LANGUAGES = [("en", "Inglês"), ("es", "Espanhol"), ("fr", "Francês")]
INTERESTS = ["viagem", "trabalho", "cultura", "tecnologia", "cotidiano"]


def _redirect(url: str) -> RedirectResponse:
    return RedirectResponse(url, status_code=303)


def _set_session_cookie(response: RedirectResponse, request: Request, code: str) -> None:
    settings = request.app.state.settings
    token = sign_code(request.app.state.serializer, code)
    response.set_cookie(
        "pid",
        token,
        httponly=True,
        samesite="lax",
        max_age=180 * 24 * 3600,
        secure=settings.cookie_secure,
    )


@router.get("/")
def consent_page(request: Request, db: Session = Depends(get_db)):
    if current_participant(request, db):
        return _redirect("/app")
    return render(request, "consent.html", participant=None, error=None)


@router.post("/consentimento")
def consent_submit(
    request: Request,
    aceite: str = Form(default=""),
    csrf_token: str = Form(default=""),
    db: Session = Depends(get_db),
):
    verify_csrf(request, csrf_token)
    enforce(request, "consent", 20)
    if aceite != "on":
        return render(
            request,
            "consent.html",
            participant=None,
            error="Para continuar, é preciso aceitar o termo de consentimento.",
        )
    return render(
        request,
        "register.html",
        participant=None,
        error=None,
        form={},
        level_options=LEVEL_OPTIONS,
        languages=LANGUAGES,
        interests=INTERESTS,
    )


@router.get("/cadastro")
def register_page(request: Request):
    return render(
        request,
        "register.html",
        participant=None,
        error=None,
        form={},
        level_options=LEVEL_OPTIONS,
        languages=LANGUAGES,
        interests=INTERESTS,
    )


@router.post("/cadastro")
def register(
    request: Request,
    nome: str = Form(default=""),
    sobrenome: str = Form(default=""),
    idade: str = Form(default=""),
    nivel: str = Form(default=""),
    idiomas: list[str] = Form(default=[]),
    interesses: list[str] = Form(default=[]),
    aceite: str = Form(default=""),
    csrf_token: str = Form(default=""),
    db: Session = Depends(get_db),
):
    verify_csrf(request, csrf_token)
    enforce(request, "register", 10)
    form = {
        "nome": nome,
        "sobrenome": sobrenome,
        "idade": idade,
        "nivel": nivel,
        "idiomas": idiomas,
        "interesses": interesses,
    }
    error = None
    try:
        age = int(idade)
    except (TypeError, ValueError):
        age = 0

    if aceite != "on":
        error = "O aceite do TCLE é obrigatório."
    elif len(nome.strip()) < 2 or len(sobrenome.strip()) < 2:
        error = "Informe nome e sobrenome."
    elif age < 18:
        error = "A participação é permitida apenas para maiores de 18 anos."
    elif age > 120:
        error = "Verifique a idade informada."
    elif nivel not in ALLOWED_LEVELS:
        error = "Escolha um nível válido."
    elif not idiomas or any(code not in {"en", "es", "fr"} for code in idiomas):
        error = "Escolha pelo menos um idioma."

    if error:
        return render(
            request,
            "register.html",
            participant=None,
            error=error,
            form=form,
            level_options=LEVEL_OPTIONS,
            languages=LANGUAGES,
            interests=INTERESTS,
        )

    code = ""
    for _ in range(20):
        candidate = generate_code()
        exists = db.exec(select(Participant).where(Participant.code == candidate)).first()
        if not exists:
            code = candidate
            break
    if not code:
        return render(
            request,
            "register.html",
            participant=None,
            error="Não foi possível gerar seu código. Tente novamente.",
            form=form,
            level_options=LEVEL_OPTIONS,
            languages=LANGUAGES,
            interests=INTERESTS,
        )

    settings = request.app.state.settings
    participant = Participant(
        code=code,
        name=nome.strip(),
        surname=sobrenome.strip(),
        age=age,
        level=nivel,
        languages=json.dumps(idiomas, ensure_ascii=False),
        interests=json.dumps(interesses, ensure_ascii=False),
        consent_version=settings.tcle_version,
        consent_at=datetime.now(timezone.utc),
    )
    db.add(participant)
    db.commit()
    db.refresh(participant)
    db.add(
        Event(
            participant_id=participant.id,
            type="registered",
            payload_json=json.dumps({"level": nivel, "languages": idiomas}),
        )
    )
    db.commit()

    response = _redirect("/app")
    _set_session_cookie(response, request, code)
    return response


@router.get("/entrar")
def enter_page(request: Request, erro: str | None = None):
    return render(request, "enter.html", participant=None, error=erro)


@router.post("/entrar")
def enter(
    request: Request,
    codigo: str = Form(default=""),
    csrf_token: str = Form(default=""),
    db: Session = Depends(get_db),
):
    verify_csrf(request, csrf_token)
    enforce(request, "enter", 8)
    code = codigo.strip().upper()
    participant = db.exec(select(Participant).where(Participant.code == code)).first()
    if participant is None:
        db.add(Event(type="auth_failed", payload_json='{"area": "enter"}'))
        db.commit()
        return render(
            request,
            "enter.html",
            participant=None,
            error="Código não encontrado. Confira as letras e tente de novo.",
        )
    response = _redirect("/app")
    _set_session_cookie(response, request, participant.code)
    return response


@router.post("/sair")
def logout(request: Request, csrf_token: str = Form(default="")):
    verify_csrf(request, csrf_token)
    response = _redirect("/")
    response.delete_cookie("pid")
    return response
