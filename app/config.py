from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

try:  # .env local; em produção as variáveis vêm do provedor
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / ".env")
except ImportError:  # pragma: no cover
    pass


@dataclass
class Settings:
    app_name: str = "sabiá"
    secret_key: str = "dev-secret-troque-em-producao"
    database_url: str = ""
    llm_provider: str = "mock"  # mock | openai
    llm_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai"
    llm_api_key: str = ""
    llm_model: str = "gemini-2.5-flash"
    llm_fallback_base_url: str = ""
    llm_fallback_api_key: str = ""
    llm_fallback_model: str = ""
    llm_timeout_s: float = 40.0
    admin_password: str = ""
    required_sessions: int = 3
    instrument_version: str = "1.0"
    tcle_version: str = "1.0"
    cookie_secure: bool = False
    rate_limit_enabled: bool = True

    def __post_init__(self) -> None:
        if not self.database_url:
            self.database_url = f"sqlite:///{DATA_DIR / 'app.db'}"
        # Render/Heroku entregam postgres:// ou postgresql://; SQLAlchemy 2 + psycopg 3
        # exigem o driver explícito.
        if self.database_url.startswith("postgres://"):
            self.database_url = "postgresql+psycopg://" + self.database_url[len("postgres://") :]
        elif self.database_url.startswith("postgresql://"):
            self.database_url = "postgresql+psycopg://" + self.database_url[len("postgresql://") :]

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            secret_key=os.getenv("APP_SECRET", cls.secret_key),
            database_url=os.getenv("DATABASE_URL", ""),
            llm_provider=os.getenv("LLM_PROVIDER", cls.llm_provider).lower(),
            llm_base_url=os.getenv("LLM_BASE_URL", cls.llm_base_url).rstrip("/"),
            llm_api_key=os.getenv("LLM_API_KEY", ""),
            llm_model=os.getenv("LLM_MODEL", cls.llm_model),
            llm_fallback_base_url=os.getenv("LLM_FALLBACK_BASE_URL", "").rstrip("/"),
            llm_fallback_api_key=os.getenv("LLM_FALLBACK_API_KEY", ""),
            llm_fallback_model=os.getenv("LLM_FALLBACK_MODEL", ""),
            llm_timeout_s=float(os.getenv("LLM_TIMEOUT_S", str(cls.llm_timeout_s))),
            admin_password=os.getenv("ADMIN_PASSWORD", ""),
            required_sessions=int(os.getenv("REQUIRED_SESSIONS", "3")),
            instrument_version=os.getenv("INSTRUMENT_VERSION", cls.instrument_version),
            tcle_version=os.getenv("TCLE_VERSION", cls.tcle_version),
            cookie_secure=os.getenv("APP_COOKIE_SECURE", "0") == "1",
            rate_limit_enabled=os.getenv("RATE_LIMIT_ENABLED", "1") == "1",
        )
