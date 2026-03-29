"""Pydantic schemas for request/response validation."""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Tutoring endpoints
# ---------------------------------------------------------------------------

class ExplainRequest(BaseModel):
    session_id: str
    topic_id: str


class QuestionRequest(BaseModel):
    session_id: str
    topic_id: str


class AnswerRequest(BaseModel):
    session_id: str
    topic_id: str
    question: str
    correct_answer: str
    student_answer: str


class ChatRequest(BaseModel):
    session_id: str
    topic_id: str
    message: str
    history: list[dict] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Diagnostic quiz
# ---------------------------------------------------------------------------

class DiagnosticAnswer(BaseModel):
    question: str
    student_answer: str
    correct_answer: str
    is_correct: bool


class DiagnosticRequest(BaseModel):
    session_id: str
    topic: str = "algebra"
    answers: list[DiagnosticAnswer]


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------

class SessionCreateRequest(BaseModel):
    initial_topic: Optional[str] = "arithmetic"
    initial_level: Optional[str] = "beginner"
