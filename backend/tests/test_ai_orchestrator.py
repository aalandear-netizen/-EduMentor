"""Tests for AI Orchestrator – uses mocked LangChain ainvoke responses."""
from __future__ import annotations

import json
import pytest
from unittest.mock import AsyncMock, MagicMock
from langchain_core.messages import AIMessage

from app.services.ai_orchestrator import AIOrchestrator, QuestionResponse, DiagnosticResult


@pytest.fixture
def orchestrator(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-dummy-key")
    monkeypatch.setenv("OPENAI_API_BASE", "https://openrouter.ai/api/v1")
    monkeypatch.setenv("OPENAI_MODEL", "openai/gpt-oss-120b:free")
    return AIOrchestrator()


@pytest.fixture
def orchestrator_openrouter(monkeypatch):
    """Orchestrator configured like an OpenRouter endpoint."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-or-test-dummy-key")
    monkeypatch.setenv("OPENAI_API_BASE", "https://openrouter.ai/api/v1")
    monkeypatch.setenv("OPENAI_MODEL", "openai/gpt-oss-120b:free")
    return AIOrchestrator()


def _mock_llm(content: str) -> MagicMock:
    """Return a mock that replaces orchestrator.llm with ainvoke returning an AIMessage."""
    mock = MagicMock()
    mock.ainvoke = AsyncMock(return_value=AIMessage(content=content))
    return mock


@pytest.mark.asyncio
async def test_generate_explanation(orchestrator):
    mock_content = "Linear equations are equations where the variable appears to the first power."
    orchestrator.llm = _mock_llm(mock_content)
    result = await orchestrator.generate_explanation(
        topic_label="Algebra Basics",
        topic_description="Linear equations and inequalities.",
        level="beginner",
    )
    assert result == mock_content


@pytest.mark.asyncio
async def test_generate_question(orchestrator):
    payload = {
        "question": "Solve: 2x + 3 = 7",
        "answer": "x = 2",
        "explanation": "Subtract 3 from both sides: 2x = 4. Divide by 2: x = 2.",
        "hint": "Start by isolating the variable.",
    }
    orchestrator.llm = _mock_llm(json.dumps(payload))
    result = await orchestrator.generate_question(
        topic_label="Algebra Basics",
        level="beginner",
        difficulty=2,
    )
    assert isinstance(result, QuestionResponse)
    assert result.question == payload["question"]
    assert result.answer == payload["answer"]
    assert result.hint == payload["hint"]


@pytest.mark.asyncio
async def test_generate_feedback_correct(orchestrator):
    mock_feedback = "Great job! Your answer is correct."
    orchestrator.llm = _mock_llm(mock_feedback)
    result = await orchestrator.generate_feedback(
        question="Solve: x + 1 = 3",
        correct_answer="x = 2",
        student_answer="x = 2",
        is_correct=True,
        level="beginner",
    )
    assert result == mock_feedback


@pytest.mark.asyncio
async def test_assess_diagnostic(orchestrator):
    payload = {
        "level": "intermediate",
        "reasoning": "Student got basic questions right but struggled with quadratics.",
        "suggested_topic": "algebra_intermediate",
    }
    orchestrator.llm = _mock_llm(json.dumps(payload))
    result = await orchestrator.assess_diagnostic(
        topic="algebra",
        answers=[
            {"question": "2+2", "student_answer": "4", "correct_answer": "4", "is_correct": True},
            {"question": "x^2=4", "student_answer": "x=4", "correct_answer": "x=±2", "is_correct": False},
        ],
    )
    assert isinstance(result, DiagnosticResult)
    assert result.level == "intermediate"
    assert result.suggested_topic == "algebra_intermediate"


@pytest.mark.asyncio
async def test_chat(orchestrator):
    mock_reply = "Sure! Let's work through this step by step."
    orchestrator.llm = _mock_llm(mock_reply)
    result = await orchestrator.chat(
        message="Can you help me understand derivatives?",
        topic_label="Calculus – Derivatives",
        level="intermediate",
        history=[],
    )
    assert result == mock_reply


# ---------------------------------------------------------------------------
# OpenRouter / LangChain ChatOpenAI configuration tests
# ---------------------------------------------------------------------------

def test_openrouter_base_url_forwarded(orchestrator_openrouter):
    """ChatOpenAI must receive the OpenRouter base URL from OPENAI_API_BASE."""
    assert "openrouter.ai" in (orchestrator_openrouter.llm.openai_api_base or "")


def test_openrouter_model_name(orchestrator_openrouter):
    """Model name must include the :free suffix from OPENAI_MODEL."""
    assert orchestrator_openrouter.model == "openai/gpt-oss-120b:free"
    assert orchestrator_openrouter.llm.model_name == "openai/gpt-oss-120b:free"


def test_default_model_is_gpt_oss_120b_free(monkeypatch):
    """Default model (no OPENAI_MODEL env var) should be openai/gpt-oss-120b:free."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-dummy-key")
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    orch = AIOrchestrator()
    assert orch.model == "openai/gpt-oss-120b:free"


def test_gpt_oss_20b_free_model_name(monkeypatch):
    """OPENAI_MODEL=openai/gpt-oss-20b:free must be picked up correctly."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-dummy-key")
    monkeypatch.setenv("OPENAI_API_BASE", "https://openrouter.ai/api/v1")
    monkeypatch.setenv("OPENAI_MODEL", "openai/gpt-oss-20b:free")
    orch = AIOrchestrator()
    assert orch.model == "openai/gpt-oss-20b:free"
    assert orch.llm.model_name == "openai/gpt-oss-20b:free"


def test_default_base_url_is_openrouter(monkeypatch):
    """When OPENAI_API_BASE is not set, base URL should fall back to the OpenRouter default."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-dummy-key")
    monkeypatch.delenv("OPENAI_API_BASE", raising=False)
    orch = AIOrchestrator()
    assert "openrouter.ai" in (orch.llm.openai_api_base or "")


@pytest.mark.asyncio
async def test_generate_explanation_with_openrouter(orchestrator_openrouter):
    """generate_explanation works end-to-end with an OpenRouter-style orchestrator."""
    mock_content = "Derivatives measure the rate of change of a function."
    orchestrator_openrouter.llm = _mock_llm(mock_content)
    result = await orchestrator_openrouter.generate_explanation(
        topic_label="Calculus – Derivatives",
        topic_description="Differentiation rules and applications.",
        level="intermediate",
    )
    assert result == mock_content

