from __future__ import annotations

import sys
from pathlib import Path

from app.services.lessons import validate_directory


def main() -> int:
    directory = Path(__file__).resolve().parents[2] / "data" / "lessons"
    problems = validate_directory(directory)
    if problems:
        print("Problemas encontrados:")
        for problem in problems:
            print(f" - {problem}")
        return 1
    print(f"OK: {directory} validado (3 idiomas × 20 lições).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
