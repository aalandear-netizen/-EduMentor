"""Knowledge graph API endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.services.knowledge_graph import KnowledgeGraphService

router = APIRouter()

_kg = KnowledgeGraphService()


@router.get("/topics")
async def list_topics():
    """Return all topics in the knowledge graph."""
    return {"topics": _kg.get_all_topics()}


@router.get("/topics/{topic_id}")
async def get_topic(topic_id: str):
    """Return details for a single topic."""
    topic = _kg.get_topic(topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail=f"Topic '{topic_id}' not found.")
    return topic


@router.get("/topics/{topic_id}/next")
async def get_next_topic(topic_id: str):
    """Return the next recommended topic after mastering *topic_id*."""
    next_id = _kg.get_next_topic(topic_id)
    if not next_id:
        return {"topic_id": topic_id, "next_topic": None, "message": "You have reached the end of this path!"}
    topic = _kg.get_topic(next_id)
    return {"topic_id": topic_id, "next_topic": topic}


@router.get("/topics/{topic_id}/prerequisites")
async def get_prerequisites(topic_id: str):
    """Return prerequisite topics for a given topic."""
    prereqs = _kg.get_prerequisites(topic_id)
    topics = [_kg.get_topic(p) for p in prereqs]
    return {"topic_id": topic_id, "prerequisites": [t for t in topics if t]}


@router.get("/entry-points")
async def get_entry_points():
    """Return topics with no prerequisites (entry points)."""
    entries = _kg.get_entry_topics()
    return {"entry_topics": [_kg.get_topic(t) for t in entries]}
