from __future__ import annotations

from typing import Any

SYSTEM_TURN = """Você é uma professora de idiomas para brasileiros, paciente e direta.

Regras:
1. A conversa acontece no idioma estudado; explicações em português do Brasil.
2. Corrija erros de gramática, vocabulário, ortografia e naturalidade.
3. Seja curta: no máximo 3 frases na resposta conversacional.
4. Respeite o nível da lição; não avance demais.
5. Responda SOMENTE com um objeto JSON válido, sem markdown e sem texto fora dele.

Formato exato:
{"resposta": "no idioma estudado", "correcao": "curta, em PT-BR",
 "explicacao": "curta, em PT-BR", "exemplo": "no idioma estudado",
 "nota": 0, "proximo_passo": "em PT-BR",
 "erros": [{"tipo": "gramatica", "trecho": "...", "correcao": "..."}]}

Use "erros": [] quando não houver erro. "nota" é de 0 a 10.
"""

SYSTEM_FEEDBACK = """Você é a professora que fecha a aula. Produza um feedback final em Markdown,
em português do Brasil, com os títulos: Resumo, Acertos, Pontos de atenção, Nota final
e Próximo passo. Seja específica e curta (até 200 palavras). Não invente dados.
"""


def lesson_context(lesson: dict, language: str, mode: str) -> str:
    content = ", ".join(lesson.get("content", [])[:6])
    parts = [
        f"Idioma: {language}",
        f"Lição {lesson.get('id')} — {lesson.get('theme')} ({lesson.get('level')})",
        f"Objetivo: {lesson.get('objective')}",
        f"Modo: {mode}",
        f"Conteúdo: {content}",
    ]
    reading = lesson.get("reading") or {}
    if reading.get("text"):
        parts.append(f"Texto de apoio — {reading.get('title', '')}: {reading['text'][:700]}")
    return "\n".join(parts)


def turn_messages(
    lesson: dict,
    language: str,
    mode: str,
    history: list[dict[str, str]],
    message: str,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    recent = history[-10:]
    history_text = "\n".join(f"{turn['role']}: {turn['content']}" for turn in recent)
    user = (
        f"{lesson_context(lesson, language, mode)}\n\n"
        f"Histórico recente:\n{history_text or '(início)'}\n\n"
        f"Mensagem atual do aluno:\n{message}"
    )
    meta = {
        "purpose": "turn",
        "lesson": lesson,
        "language": language,
        "mode": mode,
        "message": message,
    }
    return [
        {"role": "system", "content": SYSTEM_TURN},
        {"role": "user", "content": user},
    ], meta


def feedback_messages(
    lesson: dict,
    language: str,
    mode: str,
    history: list[dict[str, str]],
    score: float | None,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    history_text = "\n".join(f"{turn['role']}: {turn['content']}" for turn in history[-20:])
    user = (
        f"{lesson_context(lesson, language, mode)}\n\n"
        f"Nota média dos turnos: {score if score is not None else 'sem nota'}\n\n"
        f"Histórico da aula:\n{history_text or '(sem interações)'}"
    )
    meta = {
        "purpose": "feedback",
        "lesson": lesson,
        "language": language,
        "mode": mode,
        "score": score,
    }
    return [
        {"role": "system", "content": SYSTEM_FEEDBACK},
        {"role": "user", "content": user},
    ], meta
