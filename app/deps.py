from __future__ import annotations

from fastapi import Depends, Request
from sqlmodel import Session, select

from .db import get_db
from .models import Participant
from .security import read_code


def current_participant(
    request: Request, db: Session = Depends(get_db)
) -> Participant | None:
    code = read_code(request.app.state.serializer, request.cookies.get("pid"))
    if not code:
        return None
    return db.exec(select(Participant).where(Participant.code == code)).first()
