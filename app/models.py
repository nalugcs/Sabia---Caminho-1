from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class Participant(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(index=True, unique=True)
    name: str
    surname: str
    age: int
    level: str
    languages: str = "[]"
    interests: str = "[]"
    consent_version: str = ""
    consent_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PracticeSession(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    participant_id: int = Field(index=True, foreign_key="participant.id")
    lesson_id: int
    language: str
    mode: str = "conversa"
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: Optional[datetime] = None
    completed: bool = False
    score: Optional[float] = None
    feedback_text: str = ""


class Turn(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(index=True, foreign_key="practicesession.id")
    role: str  # user | assistant
    content: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    latency_ms: int = 0
    model: str = ""
    tokens_in: int = 0
    tokens_out: int = 0


class TurnEvaluation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    turn_id: int = Field(index=True, foreign_key="turn.id")
    score: Optional[int] = None
    errors_json: str = "[]"
    feedback: str = ""


class ExerciseAttempt(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    participant_id: int = Field(index=True, foreign_key="participant.id")
    session_id: int = Field(index=True, foreign_key="practicesession.id")
    lesson_id: int
    language: str
    exercise_index: int
    chosen: str
    correct: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class LessonProgress(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    participant_id: int = Field(index=True, foreign_key="participant.id")
    lesson_id: int
    language: str
    status: str = "em_andamento"  # em_andamento | concluida
    best_score: Optional[float] = None
    attempts: int = 0


class FeedbackResponse(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    participant_id: int = Field(index=True, foreign_key="participant.id")
    session_id: Optional[int] = Field(default=None, index=True)
    kind: str  # pre | micro | final
    instrument_version: str = ""
    answers_json: str = "{}"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Event(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    participant_id: Optional[int] = Field(default=None, index=True)
    type: str = Field(index=True)
    payload_json: str = "{}"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
