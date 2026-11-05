from __future__ import annotations

import json
import re
from typing import Any, Optional


def parse_json_object(text: str) -> Optional[dict[str, Any]]:
    """Extrai o primeiro objeto JSON de uma resposta de LLM."""

    if not text or not text.strip():
        return None
    candidate = text.strip()
    fenced = re.match(r"^```[a-zA-Z0-9_-]*\s*(.*?)\s*```$", candidate, re.DOTALL)
    if fenced:
        candidate = fenced.group(1).strip()

    for chunk in (candidate, _slice_object(candidate)):
        if not chunk:
            continue
        try:
            data = json.loads(chunk)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(data, dict):
            return data
    return None


def _slice_object(text: str) -> Optional[str]:
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return None
    return text[start : end + 1]
