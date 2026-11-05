from __future__ import annotations

import secrets

from fastapi import HTTPException, Request
from itsdangerous import BadSignature, URLSafeSerializer

ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def make_serializer(secret_key: str) -> URLSafeSerializer:
    return URLSafeSerializer(secret_key, salt="participant")


def make_admin_serializer(secret_key: str) -> URLSafeSerializer:
    return URLSafeSerializer(secret_key, salt="admin")


def generate_code(length: int = 6) -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(length))


def sign_code(serializer: URLSafeSerializer, code: str) -> str:
    return serializer.dumps({"code": code})


def read_code(serializer: URLSafeSerializer, token: str | None) -> str | None:
    if not token:
        return None
    try:
        data = serializer.loads(token)
    except BadSignature:
        return None
    code = data.get("code") if isinstance(data, dict) else None
    return code if isinstance(code, str) else None


def sign_admin(serializer: URLSafeSerializer) -> str:
    return serializer.dumps({"admin": True})


def is_admin(serializer: URLSafeSerializer, token: str | None) -> bool:
    if not token:
        return False
    try:
        data = serializer.loads(token)
    except BadSignature:
        return False
    return bool(isinstance(data, dict) and data.get("admin"))


def verify_csrf(request: Request, token: str | None) -> None:
    """Valida o token double-submit (cookie + formulário/cabeçalho)."""

    cookie = request.cookies.get("csrf")
    if not cookie or not token or not secrets.compare_digest(cookie, token):
        raise HTTPException(
            status_code=403,
            detail="Sessão de segurança inválida. Recarregue a página e tente de novo.",
        )
