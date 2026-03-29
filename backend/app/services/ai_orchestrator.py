"""
AI Orchestrator service – wraps the OpenAI API to generate:
  - Explanations tailored to student level
  - Practice questions with structured JSON output
  - Adaptive feedback and hints
"""
from __future__ import annotations

import json
import os
from typing import Optional

from openai import AsyncOpenAI
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
    """Async OpenAI-compatible content generator for EduMentor.

    Supports any OpenAI-compatible endpoint (e.g. OpenRouter) via the
    ``OPENAI_API_BASE`` environment variable.  When set, it is forwarded as
    ``base_url`` to the ``AsyncOpenAI`` client, enabling models such as
    ``openai/gpt-oss-120b`` or ``openai/gpt-oss-20b`` served through
    OpenRouter (https://openrouter.ai/api/v1).
    """

    def __init__(self) -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("OPENAI_MODEL", "openai/gpt-oss-120b")
        base_url = os.getenv("OPENAI_API_BASE") or None
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)

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

        response = await self._client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
            temperature=0.7,
            max_tokens=400,
        )
        return response.choices[0].message.content or ""

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

        response = await self._client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
            temperature=0.8,
            max_tokens=500,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content or "{}"
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

        response = await self._client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
            temperature=0.7,
            max_tokens=200,
        )
        return response.choices[0].message.content or ""

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

        response = await self._client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
            temperature=0.3,
            max_tokens=200,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content or "{}"
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
        messages = [{"role": "system", "content": system}]
        messages.extend(history[-10:])  # keep last 10 turns for context
        messages.append({"role": "user", "content": message})

        response = await self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.7,
            max_tokens=600,
        )
        return response.choices[0].message.content or ""
