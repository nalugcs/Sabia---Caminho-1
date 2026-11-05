from __future__ import annotations

import json
from pathlib import Path

REQUIRED_LEVELS = {"Básico", "Intermediário", "Avançado", "Fluente"}


class LessonCatalog:
    def __init__(self, directory: Path) -> None:
        self.directory = Path(directory)
        self._languages: dict[str, dict] = {}
        for path in sorted(self.directory.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            self._validate(path, data)
            self._languages[data["code"]] = data

        if not self._languages:
            raise ValueError(f"nenhum arquivo de lições em {self.directory}")

    @staticmethod
    def _validate(path: Path, data: dict) -> None:
        code = data.get("code")
        lessons = data.get("lessons")
        if not code or not isinstance(lessons, list) or len(lessons) != 20:
            raise ValueError(f"{path.name}: esperado code e 20 lições")
        ids = set()
        for lesson in lessons:
            lesson_id = lesson.get("id")
            if not isinstance(lesson_id, int) or not (1 <= lesson_id <= 20) or lesson_id in ids:
                raise ValueError(f"{path.name}: id inválido {lesson_id!r}")
            ids.add(lesson_id)
            if lesson.get("level") not in REQUIRED_LEVELS:
                raise ValueError(f"{path.name}: nível inválido na lição {lesson_id}")
            for exercise in lesson.get("exercises", []):
                if exercise.get("answer") not in exercise.get("options", []):
                    raise ValueError(
                        f"{path.name}: gabarito fora das opções (lição {lesson_id})"
                    )
        if ids != set(range(1, 21)):
            raise ValueError(f"{path.name}: ids devem ser 1..20")

    def languages(self) -> list[dict]:
        return list(self._languages.values())

    def get_language(self, code: str) -> dict | None:
        return self._languages.get(code)

    def get(self, code: str, lesson_id: int) -> dict | None:
        language = self._languages.get(code)
        if language is None:
            return None
        for lesson in language["lessons"]:
            if lesson["id"] == lesson_id:
                return lesson
        return None


def validate_directory(directory: Path) -> list[str]:
    """Valida todos os arquivos e devolve a lista de problemas (vazia = ok)."""

    problems: list[str] = []
    for path in sorted(Path(directory).glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            LessonCatalog._validate(path, data)
        except Exception as exc:  # noqa: BLE001 - ferramenta de validação
            problems.append(f"{path.name}: {exc}")
    return problems
