"""
Adaptive recommender service.

Tracks per-session topic performance and adjusts difficulty + next-topic
selection based on student responses.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TopicState:
    topic_id: str
    correct: int = 0
    incorrect: int = 0
    current_difficulty: int = 1  # 1 (easy) – 5 (hard)
    mastered: bool = False

    @property
    def total(self) -> int:
        return self.correct + self.incorrect

    @property
    def streak_correct(self) -> int:
        return self.correct  # simplified – reset on wrong answer

    def record_answer(self, is_correct: bool) -> None:
        if is_correct:
            self.correct += 1
            self._maybe_increase_difficulty()
        else:
            self.incorrect += 1
            self.correct = 0  # reset streak
            self._maybe_decrease_difficulty()

    def _maybe_increase_difficulty(self) -> None:
        if self.correct >= 3 and self.current_difficulty < 5:
            self.current_difficulty = min(5, self.current_difficulty + 1)
            self.correct = 0
        if self.current_difficulty == 5 and self.correct >= 3:
            self.mastered = True

    def _maybe_decrease_difficulty(self) -> None:
        if self.incorrect >= 2 and self.current_difficulty > 1:
            self.current_difficulty = max(1, self.current_difficulty - 1)
            self.incorrect = 0


@dataclass
class SessionState:
    session_id: str
    student_level: str = "beginner"  # beginner | intermediate | advanced
    current_topic: str = "arithmetic"
    topics: dict[str, TopicState] = field(default_factory=dict)

    def get_or_create_topic_state(self, topic_id: str) -> TopicState:
        if topic_id not in self.topics:
            self.topics[topic_id] = TopicState(topic_id=topic_id)
        return self.topics[topic_id]

    @property
    def mastered_topics(self) -> set[str]:
        return {tid for tid, ts in self.topics.items() if ts.mastered}


class AdaptiveRecommender:
    """
    Manages in-memory session states and provides adaptive recommendations.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, SessionState] = {}

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    def create_session(self, session_id: str, initial_topic: str = "arithmetic",
                       initial_level: str = "beginner") -> SessionState:
        state = SessionState(
            session_id=session_id,
            current_topic=initial_topic,
            student_level=initial_level,
        )
        self._sessions[session_id] = state
        return state

    def get_session(self, session_id: str) -> Optional[SessionState]:
        return self._sessions.get(session_id)

    def get_or_create_session(self, session_id: str) -> SessionState:
        if session_id not in self._sessions:
            self.create_session(session_id)
        return self._sessions[session_id]

    # ------------------------------------------------------------------
    # Answer recording + recommendations
    # ------------------------------------------------------------------

    def record_answer(self, session_id: str, topic_id: str,
                      is_correct: bool) -> dict:
        """
        Record an answer and return the updated state with an action hint.

        Returns a dict with:
          - difficulty: current difficulty for the topic
          - mastered: whether the topic is now mastered
          - hint_recommended: True when the student is struggling
          - action: 'continue' | 'increase_difficulty' | 'decrease_difficulty' | 'next_topic'
        """
        session = self.get_or_create_session(session_id)
        ts = session.get_or_create_topic_state(topic_id)

        prev_diff = ts.current_difficulty
        ts.record_answer(is_correct)

        action = "continue"
        if ts.mastered:
            action = "next_topic"
        elif ts.current_difficulty > prev_diff:
            action = "increase_difficulty"
        elif ts.current_difficulty < prev_diff:
            action = "decrease_difficulty"

        return {
            "difficulty": ts.current_difficulty,
            "mastered": ts.mastered,
            "hint_recommended": ts.incorrect >= 2,
            "action": action,
            "correct_count": ts.correct,
            "incorrect_count": ts.incorrect,
        }

    def get_difficulty(self, session_id: str, topic_id: str) -> int:
        session = self.get_or_create_session(session_id)
        ts = session.get_or_create_topic_state(topic_id)
        return ts.current_difficulty

    def set_level(self, session_id: str, level: str) -> None:
        session = self.get_or_create_session(session_id)
        session.student_level = level
        # Map level to initial difficulty
        level_to_difficulty = {"beginner": 1, "intermediate": 2, "advanced": 4}
        for ts in session.topics.values():
            ts.current_difficulty = level_to_difficulty.get(level, 1)

    def get_progress(self, session_id: str) -> dict:
        session = self.get_or_create_session(session_id)
        return {
            "session_id": session_id,
            "student_level": session.student_level,
            "current_topic": session.current_topic,
            "mastered_topics": list(session.mastered_topics),
            "topics": {
                tid: {
                    "correct": ts.correct,
                    "incorrect": ts.incorrect,
                    "difficulty": ts.current_difficulty,
                    "mastered": ts.mastered,
                }
                for tid, ts in session.topics.items()
            },
        }
