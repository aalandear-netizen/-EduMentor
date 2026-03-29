"""Unit tests for the Adaptive Recommender."""
import pytest
from app.services.recommender import AdaptiveRecommender, TopicState


@pytest.fixture
def recommender():
    return AdaptiveRecommender()


def test_create_session(recommender):
    session = recommender.create_session("s1", "arithmetic", "beginner")
    assert session.session_id == "s1"
    assert session.current_topic == "arithmetic"
    assert session.student_level == "beginner"


def test_get_or_create_session_creates_new(recommender):
    session = recommender.get_or_create_session("new-session")
    assert session is not None
    assert session.session_id == "new-session"


def test_record_correct_answers_increases_difficulty(recommender):
    recommender.create_session("s2")
    # 3 consecutive correct answers should increase difficulty
    for _ in range(3):
        result = recommender.record_answer("s2", "arithmetic", is_correct=True)
    assert result["difficulty"] > 1


def test_record_wrong_answers_recommends_hint(recommender):
    recommender.create_session("s3")
    # 2 wrong answers should trigger hint recommendation
    recommender.record_answer("s3", "arithmetic", is_correct=False)
    result = recommender.record_answer("s3", "arithmetic", is_correct=False)
    assert result["hint_recommended"] is True


def test_mastery_after_many_correct_answers(recommender):
    recommender.create_session("s4")
    # Need to reach difficulty 5 and then get 3 more correct answers
    ts = recommender.get_or_create_session("s4").get_or_create_topic_state("arithmetic")
    ts.current_difficulty = 5
    for _ in range(3):
        recommender.record_answer("s4", "arithmetic", is_correct=True)
    result = recommender.record_answer("s4", "arithmetic", is_correct=True)
    assert result["mastered"] is True or result["action"] == "next_topic"


def test_set_level_updates_session(recommender):
    recommender.create_session("s5")
    recommender.set_level("s5", "advanced")
    session = recommender.get_session("s5")
    assert session.student_level == "advanced"


def test_get_progress_structure(recommender):
    recommender.create_session("s6", "algebra_basics", "intermediate")
    progress = recommender.get_progress("s6")
    assert progress["session_id"] == "s6"
    assert progress["current_topic"] == "algebra_basics"
    assert progress["student_level"] == "intermediate"
    assert "mastered_topics" in progress
    assert "topics" in progress


def test_topic_state_difficulty_bounds():
    ts = TopicState(topic_id="test")
    ts.current_difficulty = 1
    # Decrease should not go below 1
    ts.incorrect = 2
    ts._maybe_decrease_difficulty()
    assert ts.current_difficulty == 1

    ts.current_difficulty = 5
    ts.correct = 3
    ts._maybe_increase_difficulty()
    # At max difficulty with 3 correct = mastery
    assert ts.mastered is True
