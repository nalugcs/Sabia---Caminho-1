from __future__ import annotations

import random


def build_exercise_view(lesson: dict, seed: int) -> list[dict]:
    """Opções embaralhadas por sessão, para o gabarito não ficar sempre em 1º."""

    rng = random.Random(seed)
    view: list[dict] = []
    for index, exercise in enumerate(lesson.get("exercises", [])):
        options = list(dict.fromkeys(exercise.get("options", [])))
        rng.shuffle(options)
        view.append(
            {
                "index": index,
                "type": exercise.get("type", ""),
                "question": exercise.get("question", ""),
                "options": options,
                "answer": exercise.get("answer", ""),
                "explanation": exercise.get("explanation", ""),
            }
        )
    return view
