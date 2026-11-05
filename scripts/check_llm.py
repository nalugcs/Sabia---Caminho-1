"""Testa o provedor de LLM real com o mesmo prompt de um turno do app.

Uso:
    cd tcc-ana/app
    LLM_PROVIDER=openai LLM_API_KEY=... LLM_BASE_URL=https://api.openai.com/v1 \
      LLM_MODEL=<modelo> .venv/bin/python scripts/check_llm.py

Para Gemini, use o base_url compatível com OpenAI que já está no .env.example.
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import Settings  # noqa: E402
from app.services.llm import LLMError, build_llm  # noqa: E402
from app.services.parsing import parse_json_object  # noqa: E402
from app.services.prompts import turn_messages  # noqa: E402


async def main() -> int:
    settings = Settings.from_env()
    print(f"provider={settings.llm_provider} model={settings.llm_model}")
    print(f"base_url={settings.llm_base_url}")

    if settings.llm_provider == "mock":
        print(
            "\nLLM_PROVIDER=mock. Defina LLM_PROVIDER=openai e LLM_API_KEY para testar.\n"
            "OpenAI:  LLM_BASE_URL=https://api.openai.com/v1\n"
            "Gemini:  LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai"
        )
        return 1

    lesson = json.loads(
        (ROOT / "data" / "lessons" / "en.json").read_text(encoding="utf-8")
    )["lessons"][0]
    messages, meta = turn_messages(
        lesson,
        "Inglês",
        "conversa",
        [],
        "Hello, my name is Ana and I is from Brazil.",
    )

    client = build_llm(settings)
    started = time.monotonic()
    try:
        response = await client.complete(
            messages,
            model=settings.llm_model,
            temperature=0.4,
            max_tokens=800,
            meta=meta,
        )
    except LLMError as exc:
        print(f"\nFALHOU: {exc}")
        return 2

    elapsed = time.monotonic() - started
    print(f"\nlatência: {elapsed:.2f}s")
    print(f"modelo: {response.model}")
    print(f"tokens: {response.prompt_tokens} in / {response.completion_tokens} out")

    data = parse_json_object(response.text)
    if not data:
        print("JSON inválido. Resposta bruta:")
        print(response.text[:800])
        return 3

    required = ["resposta", "correcao", "explicacao", "nota", "proximo_passo", "erros"]
    missing = [key for key in required if key not in data]
    if missing:
        print(f"JSON sem campos: {missing}")
        return 4

    print("JSON válido.")
    print(f"resposta: {data.get('resposta')}")
    print(f"correção: {data.get('correcao')}")
    print(f"nota: {data.get('nota')}")
    print(f"erros: {data.get('erros')}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
