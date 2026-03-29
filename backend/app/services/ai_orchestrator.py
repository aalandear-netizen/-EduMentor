"""
AI Orchestrator service – wraps LangChain's ChatOpenAI to generate:
  - Explanations tailored to student level
  - Practice questions with structured JSON output
  - Adaptive feedback and hints

Configured to use an OpenAI-compatible endpoint (default: OpenRouter) via
``OPENAI_API_BASE``.  Set ``OPENAI_MODEL`` to the exact model name including
any variant suffix (e.g. ``openai/gpt-oss-120b:free``).
"""
from __future__ import annotations

import json
import os
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class QuestionResponse(BaseModel):
    question: str = Field(description="The practice question text")
    answer: str = Field(description="The correct answer")
    explanation: str = Field(description="Step-by-step explanation of the solution")
    hint: Optional[str] = Field(default=None, description="Optional hint without revealing the answer")


class DiagnosticResult(BaseModel):
    level: str = Field(description="Detected level: beginner | intermediate | advanced")
    reasoning: str = Field(description="Brief reasoning for the level assessment")
    suggested_topic: str = Field(description="Recommended starting topic ID")


# ---------------------------------------------------------------------------
# Difficulty labels
# ---------------------------------------------------------------------------

DIFFICULTY_LABELS = {
    1: "very easy / foundational",
    2: "easy",
    3: "medium",
    4: "hard",
    5: "advanced / challenging",
}

LEVEL_LABELS = {
    "beginner": "a beginner with little prior knowledge",
    "intermediate": "an intermediate student with some background",
    "advanced": "an advanced student comfortable with the subject",
}


class AIOrchestrator:
    """LangChain-based content generator for EduMentor.

    Uses ``ChatOpenAI`` pointed at an OpenAI-compatible endpoint (default:
    OpenRouter at https://openrouter.ai/api/v1).  Key environment variables:

    - ``OPENAI_API_KEY``  – your OpenRouter (or other provider) API key
    - ``OPENAI_MODEL``    – exact model name, e.g. ``openai/gpt-oss-120b:free``
    - ``OPENAI_API_BASE`` – base URL (defaults to the OpenRouter endpoint)
    """

    #: Hard-coded OpenRouter base URL; override with ``OPENAI_API_BASE`` if needed.
    DEFAULT_API_BASE = "https://openrouter.ai/api/v1"

    def __init__(self) -> None:
        self.model = os.getenv("OPENAI_MODEL", "openai/gpt-oss-120b:free")
        self.llm = ChatOpenAI(
            model=self.model,
            temperature=0.7,
            max_tokens=1000,
            request_timeout=60,
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_api_base=os.getenv("OPENAI_API_BASE", self.DEFAULT_API_BASE),
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_messages(system: str, user: str) -> list:
        return [SystemMessage(content=system), HumanMessage(content=user)]

    @staticmethod
    def _history_to_messages(history: list[dict]) -> list:
        """Convert role/content dicts from the frontend into LangChain messages."""
        _map = {"system": SystemMessage, "user": HumanMessage, "assistant": AIMessage}
        return [_map.get(m.get("role", "user"), HumanMessage)(content=m.get("content", ""))
                for m in history]

    # ------------------------------------------------------------------
    # Explanation generation
    # ------------------------------------------------------------------

    async def generate_explanation(
        self, topic_label: str, topic_description: str,
        level: str, context: str = ""
    ) -> str:
        """Return a concise, level-appropriate explanation of a topic."""
        level_desc = LEVEL_LABELS.get(level, level)
        system = (
            "You are a patient and encouraging STEM tutor. "
            "Your explanations are clear, concise, and tailored to the student's level. "
            "Use simple analogies and concrete examples."
        )
        user = f"""The student is {level_desc}.
Topic: {topic_label}
Description: {topic_description}
{f"Previous conversation context: {context}" if context else ""}

Please provide a short, clear explanation (3–5 sentences) of this topic suitable for this student."""

        response = await self.llm.ainvoke(self._build_messages(system, user))
        return response.content or ""

    # ------------------------------------------------------------------
    # Question generation
    # ------------------------------------------------------------------

    async def generate_question(
        self, topic_label: str, level: str, difficulty: int = 1
    ) -> QuestionResponse:
        """Generate a practice question with answer, explanation, and hint."""
        difficulty_desc = DIFFICULTY_LABELS.get(difficulty, "medium")
        level_desc = LEVEL_LABELS.get(level, level)

        system = (
            "You are a STEM tutor. Generate practice questions with detailed solutions. "
            "Always respond with valid JSON matching the requested schema."
        )
        user = f"""Generate ONE practice question for the topic "{topic_label}".
Student level: {level_desc}
Difficulty: {difficulty_desc} (scale 1–5)

Respond ONLY with a JSON object with these keys:
- "question": the question text
- "answer": the correct answer
- "explanation": step-by-step solution (2–4 sentences)
- "hint": a helpful hint that does NOT reveal the answer (can be null)"""

        response = await self.llm.ainvoke(self._build_messages(system, user))
        raw = response.content or "{}"
        data = json.loads(raw)
        return QuestionResponse(
            question=data.get("question", ""),
            answer=data.get("answer", ""),
            explanation=data.get("explanation", ""),
            hint=data.get("hint"),
        )

    # ------------------------------------------------------------------
    # Feedback generation
    # ------------------------------------------------------------------

    async def generate_feedback(
        self, question: str, correct_answer: str,
        student_answer: str, is_correct: bool, level: str
    ) -> str:
        """Return encouraging feedback on the student's answer."""
        level_desc = LEVEL_LABELS.get(level, level)
        system = (
            "You are a supportive STEM tutor. Provide constructive, encouraging feedback. "
            "If the student is wrong, guide them toward the answer without giving it away. "
            "Keep responses concise (2–3 sentences)."
        )
        verdict = "correct" if is_correct else "incorrect"
        user = f"""The student ({level_desc}) answered a question {verdict}.
Question: {question}
Correct answer: {correct_answer}
Student's answer: {student_answer}

Provide brief, encouraging feedback."""

        response = await self.llm.ainvoke(self._build_messages(system, user))
        return response.content or ""

    # ------------------------------------------------------------------
    # Diagnostic quiz assessment
    # ------------------------------------------------------------------

    async def assess_diagnostic(self, topic: str, answers: list[dict]) -> DiagnosticResult:
        """Assess diagnostic quiz answers and determine student level."""
        system = (
            "You are an expert STEM educator. Assess student performance on a diagnostic quiz "
            "and determine their proficiency level. Always respond with valid JSON."
        )
        answers_text = "\n".join(
            f"Q{i+1}: {a.get('question', '')} | Student: {a.get('student_answer', '')} "
            f"| Correct: {a.get('correct_answer', '')} | {'✓' if a.get('is_correct') else '✗'}"
            for i, a in enumerate(answers)
        )
        user = f"""Topic area: {topic}
Diagnostic quiz results:
{answers_text}

Based on these results, determine the student's level.
Respond ONLY with JSON:
{{
  "level": "beginner" | "intermediate" | "advanced",
  "reasoning": "brief explanation",
  "suggested_topic": "<topic_id from: arithmetic, pre_algebra, algebra_basics, algebra_intermediate, precalculus, calculus_limits, calculus_derivatives, calculus_integrals>"
}}"""

        response = await self.llm.ainvoke(self._build_messages(system, user))
        raw = response.content or "{}"
        data = json.loads(raw)
        return DiagnosticResult(
            level=data.get("level", "beginner"),
            reasoning=data.get("reasoning", ""),
            suggested_topic=data.get("suggested_topic", "arithmetic"),
        )

    # ------------------------------------------------------------------
    # Chat / free-form Q&A
    # ------------------------------------------------------------------

    async def chat(
        self, message: str, topic_label: str, level: str,
        history: list[dict]
    ) -> str:
        """Handle a free-form student message in the tutoring context."""
        system = (
            f"You are EduMentor, a patient and encouraging STEM tutor. "
            f"The student is currently studying '{topic_label}' "
            f"and is at a {level} level. "
            "Help the student understand concepts, answer their questions, "
            "and guide them without simply giving away answers to practice problems. "
            "Keep responses focused and appropriately detailed."
        )
        messages = [SystemMessage(content=system)]
        messages.extend(self._history_to_messages(history[-10:]))
        messages.append(HumanMessage(content=message))

        response = await self.llm.ainvoke(messages)
        return response.content or ""

