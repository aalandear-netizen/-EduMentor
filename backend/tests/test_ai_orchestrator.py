"""Tests for AI Orchestrator – uses mocked OpenAI responses."""
from __future__ import annotations

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.ai_orchestrator import AIOrchestrator, QuestionResponse, DiagnosticResult


@pytest.fixture
def orchestrator(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-dummy-key")
    return AIOrchestrator()


@pytest.fixture
def orchestrator_openrouter(monkeypatch):
    """Orchestrator configured like an OpenRouter endpoint."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-or-test-dummy-key")
    monkeypatch.setenv("OPENAI_API_BASE", "https://openrouter.ai/api/v1")
    monkeypatch.setenv("OPENAI_MODEL", "openai/gpt-oss-120b")
    return AIOrchestrator()


def _make_completion(content: str):
    """Helper to build a mock ChatCompletion response."""
    choice = MagicMock()
    choice.message.content = content
    completion = MagicMock()
    completion.choices = [choice]
    return completion


@pytest.mark.asyncio
async def test_generate_explanation(orchestrator):
    mock_content = "Linear equations are equations where the variable appears to the first power."
    with patch.object(orchestrator._client.chat.completions, "create",
                      new=AsyncMock(return_value=_make_completion(mock_content))):
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
    with patch.object(orchestrator._client.chat.completions, "create",
                      new=AsyncMock(return_value=_make_completion(json.dumps(payload)))):
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
    with patch.object(orchestrator._client.chat.completions, "create",
                      new=AsyncMock(return_value=_make_completion(mock_feedback))):
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
    with patch.object(orchestrator._client.chat.completions, "create",
                      new=AsyncMock(return_value=_make_completion(json.dumps(payload)))):
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
    with patch.object(orchestrator._client.chat.completions, "create",
                      new=AsyncMock(return_value=_make_completion(mock_reply))):
        result = await orchestrator.chat(
            message="Can you help me understand derivatives?",
            topic_label="Calculus – Derivatives",
            level="intermediate",
            history=[],
        )
    assert result == mock_reply


# ---------------------------------------------------------------------------
# OpenRouter / custom base_url tests
# ---------------------------------------------------------------------------

def test_openrouter_base_url_forwarded(orchestrator_openrouter):
    """AsyncOpenAI client must receive the custom base_url from OPENAI_API_BASE."""
    base = str(orchestrator_openrouter._client.base_url)
    assert "openrouter.ai" in base


def test_openrouter_model_name(orchestrator_openrouter):
    """Model name must reflect OPENAI_MODEL env var (e.g. openai/gpt-oss-120b)."""
    assert orchestrator_openrouter.model == "openai/gpt-oss-120b"


def test_default_model_is_gpt_oss_120b(monkeypatch):
    """Default model (no OPENAI_MODEL env var) should be openai/gpt-oss-120b."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-dummy-key")
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_API_BASE", raising=False)
    orch = AIOrchestrator()
    assert orch.model == "openai/gpt-oss-120b"


def test_gpt_oss_20b_model_name(monkeypatch):
    """OPENAI_MODEL=openai/gpt-oss-20b must be picked up correctly."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-dummy-key")
    monkeypatch.setenv("OPENAI_API_BASE", "https://openrouter.ai/api/v1")
    monkeypatch.setenv("OPENAI_MODEL", "openai/gpt-oss-20b")
    orch = AIOrchestrator()
    assert orch.model == "openai/gpt-oss-20b"


def test_no_base_url_when_env_unset(monkeypatch):
    """When OPENAI_API_BASE is not set, base_url should fall back to the default OpenAI URL."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-dummy-key")
    monkeypatch.delenv("OPENAI_API_BASE", raising=False)
    orch = AIOrchestrator()
    # Default OpenAI base_url contains 'api.openai.com'
    assert "openai.com" in str(orch._client.base_url)


@pytest.mark.asyncio
async def test_generate_explanation_with_openrouter(orchestrator_openrouter):
    """generate_explanation works end-to-end with an OpenRouter-style orchestrator."""
    mock_content = "Derivatives measure the rate of change of a function."
    with patch.object(orchestrator_openrouter._client.chat.completions, "create",
                      new=AsyncMock(return_value=_make_completion(mock_content))):
        result = await orchestrator_openrouter.generate_explanation(
            topic_label="Calculus – Derivatives",
            topic_description="Differentiation rules and applications.",
            level="intermediate",
        )
    assert result == mock_content
