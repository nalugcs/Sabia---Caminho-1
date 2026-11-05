from __future__ import annotations

import logging
import secrets

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .config import DATA_DIR, Settings
from .db import create_db_engine, init_db
from .routes import admin, auth, learning
from .security import make_admin_serializer, make_serializer
from .services.lessons import LessonCatalog
from .services.llm import build_llm
from .services.ratelimit import RateLimiter
from .web import STATIC_DIR

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

APP_VERSION = "0.1.0"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()

    engine = create_db_engine(settings.database_url)
    init_db(engine)

    catalog = LessonCatalog(DATA_DIR / "lessons")
    llm = build_llm(settings)
    logger.info(
        "app iniciado com %s lições e provedor %s",
        sum(len(item["lessons"]) for item in catalog.languages()),
        settings.llm_provider,
    )

    app = FastAPI(title="sabiá", version=APP_VERSION)
    app.state.settings = settings
    app.state.engine = engine
    app.state.catalog = catalog
    app.state.llm = llm
    app.state.serializer = make_serializer(settings.secret_key)
    app.state.admin_serializer = make_admin_serializer(settings.secret_key)
    app.state.limiter = RateLimiter()

    @app.middleware("http")
    async def security_middleware(request, call_next):
        token = request.cookies.get("csrf")
        new_token = token is None
        if new_token:
            token = secrets.token_urlsafe(32)
        request.state.csrf = token

        response = await call_next(request)

        if new_token:
            response.set_cookie(
                "csrf",
                token,
                httponly=True,
                samesite="lax",
                max_age=6 * 3600,
                secure=settings.cookie_secure,
            )
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault(
            "Permissions-Policy", "camera=(), microphone=(), geolocation=()"
        )
        response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; style-src 'self'; script-src 'self'; "
            "img-src 'self' data:; font-src 'self'; form-action 'self'; "
            "frame-ancestors 'none'; base-uri 'self'",
        )
        if settings.cookie_secure:
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        if request.url.path.startswith(
            ("/app", "/licao", "/feedback", "/admin", "/questionario")
        ):
            response.headers.setdefault("Cache-Control", "no-store")
        return response

    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    app.include_router(auth.router)
    app.include_router(learning.router)
    app.include_router(admin.router)

    @app.get("/health")
    def health():
        return {
            "status": "ok",
            "version": APP_VERSION,
            "llm_provider": settings.llm_provider,
            "languages": [item["code"] for item in catalog.languages()],
            "lessons": sum(len(item["lessons"]) for item in catalog.languages()),
        }

    return app


def __getattr__(name: str):
    """Cria o app sob demanda (evita efeitos colaterais em testes)."""

    if name == "app":
        application = create_app()
        globals()["app"] = application
        return application
    raise AttributeError(name)
