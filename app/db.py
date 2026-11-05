from __future__ import annotations

from pathlib import Path

from fastapi import Request
from sqlmodel import Session, SQLModel, create_engine


def create_db_engine(url: str):
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    if url.startswith("sqlite:///"):
        path = Path(url.replace("sqlite:///", "", 1))
        path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(url, connect_args=connect_args)


def init_db(engine) -> None:
    SQLModel.metadata.create_all(engine)


def get_db(request: Request):
    with Session(request.app.state.engine) as session:
        yield session
