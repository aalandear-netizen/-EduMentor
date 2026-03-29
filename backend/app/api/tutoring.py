"""Tutoring API endpoints."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.tutoring import (
    AnswerRequest,
    ChatRequest,
    DiagnosticRequest,
    ExplainRequest,
    QuestionRequest,
    SessionCreateRequest,
)
from app.services.ai_orchestrator import AIOrchestrator
from app.services.knowledge_graph import KnowledgeGraphService
from app.services.recommender import AdaptiveRecommender

router = APIRouter()

# Shared service instances (singletons for the process lifetime)
_orchestrator = AIOrchestrator()
_kg = KnowledgeGraphService()
_recommender = AdaptiveRecommender()


def get_orchestrator() -> AIOrchestrator:
    return _orchestrator


def get_kg() -> KnowledgeGraphService:
    return _kg


def get_recommender() -> AdaptiveRecommender:
    return _recommender


# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------

@router.post("/session")
async def create_session(
    body: SessionCreateRequest,
    recommender: AdaptiveRecommender = Depends(get_recommender),
    kg: KnowledgeGraphService = Depends(get_kg),
):
    """Create a new tutoring session and return the session ID."""
    session_id = str(uuid.uuid4())
    initial_topic = body.initial_topic or (kg.get_entry_topics() or ["arithmetic"])[0]
    recommender.create_session(
        session_id=session_id,
        initial_topic=initial_topic,
        initial_level=body.initial_level or "beginner",
    )
    return {"session_id": session_id, "current_topic": initial_topic,
            "level": body.initial_level}


@router.get("/session/{session_id}/progress")
async def get_progress(
    session_id: str,
    recommender: AdaptiveRecommender = Depends(get_recommender),
):
    """Return the student's current progress summary."""
    progress = recommender.get_progress(session_id)
    return progress


# ---------------------------------------------------------------------------
# Explanation
# ---------------------------------------------------------------------------

@router.post("/explain")
async def explain(
    body: ExplainRequest,
    orchestrator: AIOrchestrator = Depends(get_orchestrator),
    kg: KnowledgeGraphService = Depends(get_kg),
    recommender: AdaptiveRecommender = Depends(get_recommender),
):
    """Generate a tailored explanation for the given topic."""
    topic = kg.get_topic(body.topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail=f"Topic '{body.topic_id}' not found.")
    session = recommender.get_or_create_session(body.session_id)
    explanation = await orchestrator.generate_explanation(
        topic_label=topic["label"],
        topic_description=topic["description"],
        level=session.student_level,
    )
    return {"topic_id": body.topic_id, "topic_label": topic["label"],
            "explanation": explanation, "level": session.student_level}


# ---------------------------------------------------------------------------
# Question generation
# ---------------------------------------------------------------------------

@router.post("/question")
async def generate_question(
    body: QuestionRequest,
    orchestrator: AIOrchestrator = Depends(get_orchestrator),
    kg: KnowledgeGraphService = Depends(get_kg),
    recommender: AdaptiveRecommender = Depends(get_recommender),
):
    """Generate a practice question for the given topic."""
    topic = kg.get_topic(body.topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail=f"Topic '{body.topic_id}' not found.")
    session = recommender.get_or_create_session(body.session_id)
    difficulty = recommender.get_difficulty(body.session_id, body.topic_id)

    question = await orchestrator.generate_question(
        topic_label=topic["label"],
        level=session.student_level,
        difficulty=difficulty,
    )
    return {
        "topic_id": body.topic_id,
        "topic_label": topic["label"],
        "difficulty": difficulty,
        "question": question.question,
        "answer": question.answer,
        "explanation": question.explanation,
        "hint": question.hint,
    }


# ---------------------------------------------------------------------------
# Answer submission + feedback
# ---------------------------------------------------------------------------

@router.post("/answer")
async def submit_answer(
    body: AnswerRequest,
    orchestrator: AIOrchestrator = Depends(get_orchestrator),
    kg: KnowledgeGraphService = Depends(get_kg),
    recommender: AdaptiveRecommender = Depends(get_recommender),
):
    """Submit a student answer, get feedback, and update adaptive state."""
    topic = kg.get_topic(body.topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail=f"Topic '{body.topic_id}' not found.")
    session = recommender.get_or_create_session(body.session_id)

    # Simple correctness check (case-insensitive strip)
    is_correct = body.student_answer.strip().lower() == body.correct_answer.strip().lower()

    rec = recommender.record_answer(body.session_id, body.topic_id, is_correct)

    feedback = await orchestrator.generate_feedback(
        question=body.question,
        correct_answer=body.correct_answer,
        student_answer=body.student_answer,
        is_correct=is_correct,
        level=session.student_level,
    )

    next_topic = None
    if rec["action"] == "next_topic":
        next_topic = kg.get_next_topic(body.topic_id)
        if next_topic:
            session.current_topic = next_topic

    return {
        "is_correct": is_correct,
        "feedback": feedback,
        "recommendation": rec,
        "next_topic": next_topic,
    }


# ---------------------------------------------------------------------------
# Free-form chat
# ---------------------------------------------------------------------------

@router.post("/chat")
async def chat(
    body: ChatRequest,
    orchestrator: AIOrchestrator = Depends(get_orchestrator),
    kg: KnowledgeGraphService = Depends(get_kg),
    recommender: AdaptiveRecommender = Depends(get_recommender),
):
    """Handle a free-form student message in the tutoring context."""
    topic = kg.get_topic(body.topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail=f"Topic '{body.topic_id}' not found.")
    session = recommender.get_or_create_session(body.session_id)

    reply = await orchestrator.chat(
        message=body.message,
        topic_label=topic["label"],
        level=session.student_level,
        history=body.history,
    )
    return {"response": reply, "topic_id": body.topic_id, "level": session.student_level}


# ---------------------------------------------------------------------------
# Diagnostic quiz assessment
# ---------------------------------------------------------------------------

@router.post("/diagnostic")
async def run_diagnostic(
    body: DiagnosticRequest,
    orchestrator: AIOrchestrator = Depends(get_orchestrator),
    recommender: AdaptiveRecommender = Depends(get_recommender),
):
    """Assess diagnostic quiz answers and set the student's level."""
    answers = [a.model_dump() for a in body.answers]
    result = await orchestrator.assess_diagnostic(topic=body.topic, answers=answers)

    recommender.set_level(body.session_id, result.level)
    session = recommender.get_or_create_session(body.session_id)
    session.current_topic = result.suggested_topic

    return {
        "session_id": body.session_id,
        "level": result.level,
        "reasoning": result.reasoning,
        "suggested_topic": result.suggested_topic,
    }
