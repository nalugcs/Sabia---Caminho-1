from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.config import Settings
from app.main import create_app
from app.models import (
    Event,
    ExerciseAttempt,
    Participant,
    PracticeSession,
    Turn,
    TurnEvaluation,
)
from app.services.exercises import build_exercise_view
from app.services.instrument import LIKERT_KEYS
from app.services.markdown_render import render_markdown

BASE = Path(__file__).resolve().parents[1]

CSRF_RE = re.compile(r'name="csrf-token" content="([^"]+)"')


def csrf(client: TestClient) -> str:
    response = client.get("/")
    match = CSRF_RE.search(response.text)
    assert match, response.text[:300]
    return match.group(1)


def make_form(**overrides) -> dict:
    values = {
        "nome": "Ana",
        "sobrenome": "César",
        "idade": "25",
        "nivel": "básico",
        "idiomas": ["en", "es"],
        "interesses": ["viagem"],
        "aceite": "on",
    }
    values.update(overrides)
    return values


@pytest.fixture()
def app(tmp_path):
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        llm_provider="mock",
        secret_key="segredo-de-teste",
        required_sessions=3,
        tcle_version="1.0",
        admin_password="senha-admin",
    )
    return create_app(settings)


@pytest.fixture()
def client(app):
    with TestClient(app) as test_client:
        yield test_client


def register(client, **overrides):
    data = make_form(**overrides)
    data["csrf_token"] = csrf(client)
    return client.post("/cadastro", data=data, follow_redirects=False)


def lesson_session(client, language="en", lesson_id=1) -> int:
    page = client.get(f"/licao/{language}/{lesson_id}")
    return int(re.search(r'data-session="(\d+)"', page.text).group(1))


def send_turn(client, session_id: int, message: str, *, csrf_ok: bool = True):
    headers = {"X-CSRF-Token": csrf(client)} if csrf_ok else {}
    return client.post(
        "/api/turno",
        json={"session_id": session_id, "message": message},
        headers=headers,
    )


class TestBasics:
    def test_health(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["lessons"] == 60

    def test_consent_page(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert "Termo de Consentimento" in response.text
        assert "Para participar" in response.text
        assert CSRF_RE.search(response.text)

    def test_consent_requires_checkbox(self, client):
        response = client.post(
            "/consentimento", data={"csrf_token": csrf(client)}
        )
        assert response.status_code == 200
        assert "aceitar o termo" in response.text

    def test_consent_opens_registration(self, client):
        response = client.post(
            "/consentimento",
            data={"aceite": "on", "csrf_token": csrf(client)},
        )
        assert response.status_code == 200
        assert 'name="nome"' in response.text

    def test_security_headers(self, client):
        response = client.get("/")
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert "default-src 'self'" in response.headers["Content-Security-Policy"]
        assert "csrf" in client.cookies

    def test_csrf_blocks_form_without_token(self, client):
        response = client.post("/cadastro", data=make_form())
        assert response.status_code == 403


class TestRegistration:
    def test_underage_is_blocked(self, client):
        response = register(client, idade="16")
        assert response.status_code == 200
        assert "maiores de 18" in response.text

    def test_register_sets_cookie_and_dashboard(self, client):
        response = register(client)
        assert response.status_code == 303
        assert response.headers["location"] == "/app"
        assert "pid" in response.cookies

        dashboard = client.get("/app")
        assert dashboard.status_code == 200
        assert "Olá, Ana" in dashboard.text
        assert re.search(r'class="mono"[^>]*>[A-Z0-9]{6}<', dashboard.text)

    def test_register_requires_language(self, client):
        response = register(client, idiomas=[])
        assert response.status_code == 200
        assert "pelo menos um idioma" in response.text

    def test_enter_with_saved_code(self, app, client):
        register(client)
        code = re.search(r'class="mono"[^>]*>([A-Z0-9]{6})<', client.get("/app").text).group(1)

        with TestClient(app) as fresh:
            token = csrf(fresh)
            response = fresh.post(
                "/entrar",
                data={"codigo": code, "csrf_token": token},
                follow_redirects=False,
            )
            assert response.status_code == 303
            assert "pid" in response.cookies
            assert fresh.get("/app").status_code == 200

    def test_enter_rate_limit(self, client):
        token = csrf(client)
        statuses = [
            client.post(
                "/entrar", data={"codigo": "XXXXXX", "csrf_token": token}
            ).status_code
            for _ in range(9)
        ]
        assert 429 in statuses


class TestLessonFlow:
    def test_lesson_page_creates_session_and_opening(self, client):
        register(client)
        response = client.get("/licao/en/1")
        assert response.status_code == 200
        assert "Apresentação pessoal" in response.text
        assert "data-session=" in response.text
        assert "Vamos praticar" in response.text

    def test_turn_requires_csrf(self, client):
        register(client)
        session_id = lesson_session(client)
        response = send_turn(client, session_id, "Hello, my name is Ana.", csrf_ok=False)
        assert response.status_code == 403

    def test_turn_returns_score_and_persists(self, client, app):
        register(client)
        session_id = lesson_session(client)
        response = send_turn(client, session_id, "Hello, my name is Ana.")
        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is True
        assert body["resposta"]
        assert isinstance(body["score"], int)

        with Session(app.state.engine) as db:
            turns = db.exec(select(Turn).where(Turn.session_id == session_id)).all()
            evaluations = db.exec(select(TurnEvaluation)).all()
        assert len(turns) == 3  # abertura + aluno + assistente
        assert len(evaluations) == 1

    def test_finish_and_feedback(self, client):
        register(client)
        session_id = lesson_session(client, "es", 2)
        send_turn(client, session_id, "Hola, soy Ana.")
        finish = client.post(
            "/api/encerrar",
            json={"session_id": session_id},
            headers={"X-CSRF-Token": csrf(client)},
        )
        assert finish.status_code == 200
        assert finish.json()["ok"] is True

        feedback = client.get(f"/feedback/{session_id}")
        assert feedback.status_code == 200
        assert "Fim da aula" in feedback.text
        assert "Nota final" in feedback.text
        assert "<h2>Resumo</h2>" in feedback.text
        assert "## Resumo" not in feedback.text

    def test_markdown_is_sanitized(self):
        html = render_markdown("<script>alert(1)</script>\n\n## Título\n\n**forte**")
        assert "<script" not in html
        assert "<h2>Título</h2>" in html
        assert "<strong>forte</strong>" in html

    def test_micro_has_no_preselected_answer(self, client):
        register(client)
        session_id = lesson_session(client, "en", 1)
        send_turn(client, session_id, "Hello, my name is Ana.")
        finish = client.post(
            "/api/encerrar",
            json={"session_id": session_id},
            headers={"X-CSRF-Token": csrf(client)},
        )
        assert finish.status_code == 200
        feedback = client.get(f"/feedback/{session_id}")
        assert 'value="4" checked' not in feedback.text
        assert 'name="m1"' in feedback.text

    def test_practice_page_has_several_items_and_api(self, client):
        register(client)
        page = client.get("/praticar")
        assert page.status_code == 200
        assert page.text.count("data-practice-card") >= 5
        session_id = int(re.search(r'data-session="(\d+)"', page.text).group(1))
        choice = re.search(r'data-choice="([^"]+)"', page.text).group(1)
        response = client.post(
            "/api/pratica",
            json={"session_id": session_id, "index": 0, "choice": choice},
            headers={"X-CSRF-Token": csrf(client)},
        )
        assert response.status_code == 200
        assert response.json()["ok"] is True

    def test_tabs_and_code_modal(self, client):
        register(client)
        page = client.get("/app")
        for href in ("/praticar", "/jogar", "/conversar"):
            assert f'href="{href}"' in page.text
        assert "data-code-modal" in page.text
        assert "A1 — Iniciante" in client.get("/cadastro").text

    def test_cefr_changes_prompt(self):
        from app.services.prompts import turn_messages

        lesson = json.loads((BASE / "data" / "lessons" / "en.json").read_text("utf-8"))[
            "lessons"
        ][0]
        a1, _ = turn_messages(lesson, "Inglês", "conversa", [], "Hello", cefr="A1")
        c1, _ = turn_messages(lesson, "Inglês", "conversa", [], "Hello", cefr="C1")
        assert "Nível CEFR do participante: A1" in a1[1]["content"]
        assert "Nível CEFR do participante: C1" in c1[1]["content"]
        assert a1[1]["content"] != c1[1]["content"]

    def test_micro_survey(self, client):
        register(client)
        session_id = lesson_session(client, "fr", 3)
        response = client.post(
            "/api/micro",
            json={"session_id": session_id, "answers": {"m1": 4, "m2": 5, "m3": 3}},
            headers={"X-CSRF-Token": csrf(client)},
        )
        assert response.status_code == 200
        assert response.json()["ok"] is True

    def test_lesson_shows_practice(self, client):
        register(client)
        page = client.get("/licao/en/1")
        assert page.status_code == 200
        assert "data-practice" in page.text
        assert 'class="option"' in page.text

    def test_exercise_attempt_records(self, client, app):
        register(client)
        session_id = lesson_session(client)
        lesson = json.loads((BASE / "data" / "lessons" / "en.json").read_text("utf-8"))["lessons"][0]
        exercise = lesson["exercises"][0]
        wrong = next(option for option in exercise["options"] if option != exercise["answer"])
        headers = {"X-CSRF-Token": csrf(client)}

        first = client.post(
            "/api/exercicio",
            json={"session_id": session_id, "exercise_index": 0, "choice": wrong},
            headers=headers,
        )
        assert first.status_code == 200
        assert first.json()["correct"] is False
        assert first.json()["answer"] == exercise["answer"]

        second = client.post(
            "/api/exercicio",
            json={"session_id": session_id, "exercise_index": 0, "choice": exercise["answer"]},
            headers=headers,
        )
        assert second.status_code == 200
        assert second.json()["correct"] is True

        with Session(app.state.engine) as db:
            attempts = db.exec(select(ExerciseAttempt)).all()
        assert len(attempts) == 1
        assert attempts[0].correct is True

    def test_exercise_options_are_shuffled(self):
        lesson = json.loads((BASE / "data" / "lessons" / "en.json").read_text("utf-8"))["lessons"][0]
        positions = set()
        for seed in range(24):
            view = build_exercise_view(lesson, seed)
            positions.add(view[0]["options"].index(view[0]["answer"]))
        assert len(positions) > 1

    def test_turn_without_session_is_rejected(self, client):
        response = client.post(
            "/api/turno",
            json={"session_id": 1, "message": "oi"},
            headers={"X-CSRF-Token": csrf(client)},
        )
        assert response.status_code == 401

    def test_app_learns_from_recurring_error(self, client):
        register(client)
        session_id = lesson_session(client)
        send_turn(client, session_id, "I is Ana.")
        dashboard = client.get("/app")
        assert "gramática" in dashboard.text
        assert "Ponto de atenção" in dashboard.text


class TestQuestionnaire:
    def test_blocked_before_sessions(self, client):
        register(client)
        response = client.get("/questionario")
        assert response.status_code == 200
        assert "0 de 3" in response.text

    def test_submit_after_three_sessions(self, client, app):
        register(client)
        with Session(app.state.engine) as db:
            participant = db.exec(select(Participant)).first()
            for lesson_id in (1, 2, 3):
                db.add(
                    PracticeSession(
                        participant_id=participant.id,
                        lesson_id=lesson_id,
                        language="en",
                        completed=True,
                        score=8.0,
                    )
                )
            db.commit()

        page = client.get("/questionario")
        assert "Como foi a experiência?" in page.text

        answers = {key: "4" for key in LIKERT_KEYS}
        answers.update({"nps": "9", "o1": "As correções.", "o2": "Nada.", "o3": "Nada."})
        answers["csrf_token"] = csrf(client)
        response = client.post("/questionario", data=answers, follow_redirects=False)
        assert response.status_code == 303
        assert "questionario=ok" in response.headers["location"]
        assert "Questionário final respondido" in client.get("/app").text


class TestAdmin:
    def test_admin_requires_password(self, client):
        page = client.get("/admin")
        assert page.status_code == 200
        assert "Painel de dados" in page.text
        assert 'type="password"' in page.text

    def test_admin_login_and_pseudonymized_export(self, client):
        register(client)
        token = csrf(client)

        wrong = client.post(
            "/admin/entrar", data={"senha": "errada", "csrf_token": token}
        )
        assert "Senha incorreta" in wrong.text

        token = csrf(client)
        ok = client.post(
            "/admin/entrar",
            data={"senha": "senha-admin", "csrf_token": token},
            follow_redirects=False,
        )
        assert ok.status_code == 303
        assert "admin" in ok.cookies

        panel = client.get("/admin")
        assert "Exportar CSV" in panel.text

        export = client.get("/admin/exportar/participantes")
        assert export.status_code == 200
        assert "text/csv" in export.headers["content-type"]
        assert "code" in export.text
        assert "Ana" not in export.text
        assert "César" not in export.text

        with Session(client.app.state.engine) as db:
            audit = db.exec(
                select(Event)
                .where(Event.type == "admin_export")
                .order_by(Event.id.desc())
            ).first()
        assert audit is not None
        assert '"participantes"' in audit.payload_json

    def test_admin_export_requires_login(self, client):
        response = client.get("/admin/exportar/turnos", follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == "/admin"


class TestLessonsData:
    def test_three_languages_with_twenty_lessons(self):
        for code in ("en", "es", "fr"):
            data = json.loads((BASE / "data" / "lessons" / f"{code}.json").read_text("utf-8"))
            assert data["code"] == code
            assert len(data["lessons"]) == 20
            assert [lesson["id"] for lesson in data["lessons"]] == list(range(1, 21))
            for lesson in data["lessons"]:
                assert len(lesson["exercises"]) == 2
                for exercise in lesson["exercises"]:
                    assert exercise["answer"] in exercise["options"]


class TestConfig:
    def test_postgres_url_is_normalized(self):
        settings = Settings(database_url="postgresql://u:p@host/db")
        assert settings.database_url == "postgresql+psycopg://u:p@host/db"

    def test_postgres_scheme_alias_is_normalized(self):
        settings = Settings(database_url="postgres://u:p@host/db")
        assert settings.database_url == "postgresql+psycopg://u:p@host/db"
