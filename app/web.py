from __future__ import annotations

from pathlib import Path

from fastapi.templating import Jinja2Templates
from starlette.requests import Request

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def render(request: Request, name: str, **context):
    context.setdefault("csrf_token", getattr(request.state, "csrf", ""))
    context.setdefault("app_name", "Sabiá")
    return templates.TemplateResponse(request=request, name=name, context=context)
