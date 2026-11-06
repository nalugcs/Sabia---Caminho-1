"""Gera uma sessão de prática/jogo a partir dos exercícios e frases da lição.

A ideia é ter 5–10 itens sem inventar conteúdo novo: os exercícios originais
continuam sendo a base, e as frases da lição geram itens de tradução e de
completar. O nível CEFR muda o idioma do enunciado, a quantidade de opções e a
mistura de tipos.
"""

from __future__ import annotations

import random
import re

WORD_RE = re.compile(r"[A-Za-zÀ-ÿ]+(?:['’-][A-Za-zÀ-ÿ]+)?")


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        key = value.strip().lower()
        if key and key not in seen:
            seen.add(key)
            result.append(value.strip())
    return result


def _options(answer: str, pool: list[str], rng: random.Random, size: int) -> list[str]:
    distractors = [item for item in _unique(pool) if item.strip().lower() != answer.strip().lower()]
    rng.shuffle(distractors)
    options = [answer] + distractors[: max(1, size - 1)]
    options = _unique(options)
    rng.shuffle(options)
    return options


def _existing_items(lesson: dict) -> list[dict]:
    items: list[dict] = []
    for exercise in lesson.get("exercises", []):
        items.append(
            {
                "kind": exercise.get("type") or "escolha",
                "question": exercise.get("question", ""),
                "options": list(exercise.get("options", [])),
                "answer": exercise.get("answer", ""),
                "explanation": exercise.get("explanation", ""),
                "difficulty": 1,
            }
        )
    return items


TARGET_PROMPTS = {
    "en": {
        "translate": "Choose the best translation for “{target}”.",
        "complete": "Complete the sentence: “{blanked}”",
    },
    "es": {
        "translate": "Elige la mejor traducción de “{target}”.",
        "complete": "Completa la frase: “{blanked}”",
    },
    "fr": {
        "translate": "Choisissez la meilleure traduction de « {target} ».",
        "complete": "Complétez la phrase : « {blanked} »",
    },
}


def build_practice_items(
    lesson: dict,
    seed: int,
    cefr: str = "B1",
    count: int = 7,
    game: bool = False,
    language_code: str = "en",
) -> list[dict]:
    """Itens determinísticos para a mesma sessão; ``count`` fica entre 5 e 10."""

    cefr = (cefr or "B1").upper()
    low = cefr in {"A1", "A2"}
    high = cefr in {"B1", "B2", "C1", "C2"}
    rng = random.Random(seed)
    phrases = [p for p in lesson.get("phrases", []) if p.get("target") and p.get("pt")]
    translations = [p["pt"] for p in phrases]

    items = _existing_items(lesson)
    for phrase in phrases:
        target = str(phrase["target"]).strip()
        translation = str(phrase["pt"]).strip()
        target_prompts = TARGET_PROMPTS.get(language_code, TARGET_PROMPTS["en"])
        prompt = (
            f"O que significa “{target}”?"
            if low
            else target_prompts["translate"].format(target=target)
        )
        items.append(
            {
                "kind": "tradução",
                "question": prompt,
                "options": _options(translation, translations, rng, 3 if low else 4),
                "answer": translation,
                "explanation": f"{target} = {translation}",
                "difficulty": 1 if low else 2,
            }
        )

    if high:
        words = _unique(
            [word for p in phrases for word in WORD_RE.findall(str(p["target"]))]
        )
        for phrase in phrases:
            target = str(phrase["target"]).strip()
            matched = WORD_RE.findall(target)
            if not matched:
                continue
            word = max(matched, key=len)
            if len(word) < 3:
                continue
            blanked = target.replace(word, "____", 1)
            items.append(
                {
                    "kind": "completar",
                    "question": target_prompts["complete"].format(blanked=blanked),
                    "options": _options(word, words, rng, 4),
                    "answer": word,
                    "explanation": f"Frase completa: {target}",
                    "difficulty": 3,
                }
            )

    if game:
        rng.shuffle(items)
    else:
        items.sort(key=lambda item: (item["difficulty"], rng.random()))

    count = max(5, min(10, int(count)))
    return items[:count]
