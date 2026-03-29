"""Unit tests for the Knowledge Graph service."""
import pytest
from app.services.knowledge_graph import KnowledgeGraphService


@pytest.fixture
def kg():
    return KnowledgeGraphService()


def test_get_all_topics_returns_list(kg):
    topics = kg.get_all_topics()
    assert isinstance(topics, list)
    assert len(topics) > 0


def test_get_topic_exists(kg):
    topic = kg.get_topic("arithmetic")
    assert topic is not None
    assert topic["id"] == "arithmetic"
    assert "label" in topic
    assert "description" in topic


def test_get_topic_not_found(kg):
    assert kg.get_topic("nonexistent_topic") is None


def test_entry_topics_have_no_prerequisites(kg):
    entries = kg.get_entry_topics()
    assert len(entries) > 0
    for entry_id in entries:
        prereqs = kg.get_prerequisites(entry_id)
        assert prereqs == [], f"Entry topic {entry_id} should have no prerequisites"


def test_get_next_topic(kg):
    next_id = kg.get_next_topic("arithmetic")
    assert next_id == "pre_algebra"


def test_get_next_topic_end_of_path(kg):
    # Last topic in the default graph
    next_id = kg.get_next_topic("calculus_integrals")
    assert next_id is None


def test_prerequisites_met_all_present(kg):
    mastered = {"arithmetic"}
    assert kg.prerequisites_met("pre_algebra", mastered) is True


def test_prerequisites_met_missing(kg):
    mastered = set()
    assert kg.prerequisites_met("pre_algebra", mastered) is False


def test_get_prerequisites_chained(kg):
    prereqs = kg.get_prerequisites("algebra_basics")
    assert "pre_algebra" in prereqs
