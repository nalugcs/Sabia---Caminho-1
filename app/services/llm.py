from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

RETRYABLE = {429, 500, 502, 503, 504}


class LLMError(RuntimeError):
    pass


@dataclass
class LLMResponse:
    text: str
    model: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: int = 0


class LLM:
    async def complete(
        self,
        messages: list[dict[str, str]],
        *,
        model: str = "",
        temperature: float = 0.4,
        max_tokens: int = 600,
        meta: Optional[dict[str, Any]] = None,
    ) -> LLMResponse:
        raise NotImplementedError


class MockLLM(LLM):
    """Respostas determinísticas para desenvolvimento e testes."""

    async def complete(
        self,
        messages: list[dict[str, str]],
        *,
        model: str = "",
        temperature: float = 0.4,
        max_tokens: int = 600,
        meta: Optional[dict[str, Any]] = None,
    ) -> LLMResponse:
        meta = meta or {}
        if meta.get("purpose") == "feedback":
            text = self._feedback(meta)
        else:
            text = self._turn(meta)
        return LLMResponse(text=text, model="mock", prompt_tokens=80, completion_tokens=120)

    @staticmethod
    def _turn(meta: dict[str, Any]) -> str:
        lesson = meta.get("lesson") or {}
        language = meta.get("language") or "o idioma"
        phrases = lesson.get("phrases") or [{"target": "Hello!"}]
        example = phrases[0].get("target", "Hello!")
        message = (meta.get("message") or "").strip()
        errors = []
        lowered = f" {message.lower()} "
        if " i is " in lowered or " yo es " in lowered or " je suis " in lowered:
            errors.append(
                {
                    "tipo": "gramatica",
                    "trecho": message[:60],
                    "correcao": "Revise a conjugação do verbo.",
                }
            )
        nota = 9 if len(message) > 20 else 8
        payload = {
            "resposta": f"Muito bem! Vamos continuar em {language}. {example}",
            "correcao": "Sua mensagem está compreensível."
            if not errors
            else "Há um ponto de gramática para ajustar.",
            "explicacao": "Uma frase completa deixa a conversa mais natural.",
            "exemplo": example,
            "nota": nota,
            "proximo_passo": "Responda à pergunta com uma frase completa no idioma estudado.",
            "erros": errors,
        }
        return json.dumps(payload, ensure_ascii=False)

    @staticmethod
    def _feedback(meta: dict[str, Any]) -> str:
        lesson = meta.get("lesson") or {}
        score = meta.get("score")
        return (
            f"## Resumo\nVocê praticou **{lesson.get('theme', 'a lição')}** "
            f"e manteve o ritmo da conversa.\n\n"
            "## Acertos\nFrases completas e vocabulário do tema.\n\n"
            "## Pontos de atenção\nRevise a conjugação dos verbos e a ordem das palavras.\n\n"
            f"## Nota final\n{score if score is not None else '—'}/10\n\n"
            "## Próximo passo\nRepita a lição em outro modo ou avance para o próximo tema."
        )


class OpenAICompatibleLLM(LLM):
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout_s: float = 40.0,
        max_attempts: int = 3,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout_s = timeout_s
        self.max_attempts = max(1, max_attempts)

    async def complete(
        self,
        messages: list[dict[str, str]],
        *,
        model: str = "",
        temperature: float = 0.4,
        max_tokens: int = 600,
        meta: Optional[dict[str, Any]] = None,
    ) -> LLMResponse:
        payload = {
            "model": model or self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        url = f"{self.base_url}/chat/completions"
        last_error: Optional[Exception] = None

        for attempt in range(1, self.max_attempts + 1):
            started = time.monotonic()
            try:
                async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                    response = await client.post(url, json=payload, headers=headers)
                if response.status_code in RETRYABLE and attempt < self.max_attempts:
                    await asyncio.sleep(1.2 * attempt)
                    continue
                response.raise_for_status()
                data = response.json()
                choice = (data.get("choices") or [{}])[0]
                text = (choice.get("message") or {}).get("content") or ""
                usage = data.get("usage") or {}
                return LLMResponse(
                    text=text.strip(),
                    model=str(data.get("model") or payload["model"]),
                    prompt_tokens=int(usage.get("prompt_tokens") or 0),
                    completion_tokens=int(usage.get("completion_tokens") or 0),
                    latency_ms=int((time.monotonic() - started) * 1000),
                )
            except httpx.HTTPStatusError as exc:
                detail = exc.response.text[:300]
                last_error = LLMError(f"HTTP {exc.response.status_code}: {detail}")
                if exc.response.status_code not in RETRYABLE or attempt >= self.max_attempts:
                    raise last_error from exc
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                last_error = LLMError(f"falha de conexão: {exc}")
                if attempt >= self.max_attempts:
                    raise last_error from exc
            except (ValueError, KeyError, TypeError) as exc:
                raise LLMError(f"resposta inesperada do provedor: {exc}") from exc
            await asyncio.sleep(1.2 * attempt)

        raise last_error or LLMError("falha ao chamar o modelo")


class FallbackLLM(LLM):
    def __init__(self, primary: LLM, fallback: LLM) -> None:
        self.primary = primary
        self.fallback = fallback

    async def complete(self, messages, **kwargs) -> LLMResponse:
        try:
            return await self.primary.complete(messages, **kwargs)
        except LLMError as exc:
            logger.warning("provedor principal falhou, usando fallback: %s", exc)
            fallback_kwargs = dict(kwargs)
            if "model" in fallback_kwargs:
                fallback_kwargs["model"] = getattr(self.fallback, "model", fallback_kwargs["model"])
            return await self.fallback.complete(messages, **fallback_kwargs)


def build_llm(settings) -> LLM:
    if settings.llm_provider == "mock":
        return MockLLM()
    if not settings.llm_api_key:
        raise ValueError(
            "LLM_PROVIDER=openai exige LLM_API_KEY. Use LLM_PROVIDER=mock para rodar offline."
        )
    primary = OpenAICompatibleLLM(
        settings.llm_base_url, settings.llm_api_key, settings.llm_model, settings.llm_timeout_s
    )
    if settings.llm_fallback_base_url and settings.llm_fallback_api_key:
        fallback = OpenAICompatibleLLM(
            settings.llm_fallback_base_url,
            settings.llm_fallback_api_key,
            settings.llm_fallback_model or settings.llm_model,
            settings.llm_timeout_s,
        )
        return FallbackLLM(primary, fallback)
    return primary
