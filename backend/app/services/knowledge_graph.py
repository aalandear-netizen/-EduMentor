"""
Knowledge graph service – topic dependency graph stored as JSON.
Provides topic prerequisites, next-topic recommendations, and full graph export.
"""
from __future__ import annotations

import json
import os
from typing import Optional

# ---------------------------------------------------------------------------
# Default knowledge graph (algebra / calculus STEM topics as an example)
# ---------------------------------------------------------------------------
DEFAULT_GRAPH: dict = {
    "topics": {
        "arithmetic": {
            "label": "Arithmetic",
            "description": "Basic operations: addition, subtraction, multiplication, division.",
            "prerequisites": [],
            "next": ["pre_algebra"],
        },
        "pre_algebra": {
            "label": "Pre-Algebra",
            "description": "Variables, expressions, and simple equations.",
            "prerequisites": ["arithmetic"],
            "next": ["algebra_basics"],
        },
        "algebra_basics": {
            "label": "Algebra Basics",
            "description": "Linear equations, inequalities, and basic functions.",
            "prerequisites": ["pre_algebra"],
            "next": ["algebra_intermediate"],
        },
        "algebra_intermediate": {
            "label": "Intermediate Algebra",
            "description": "Quadratic equations, polynomials, and rational expressions.",
            "prerequisites": ["algebra_basics"],
            "next": ["precalculus"],
        },
        "precalculus": {
            "label": "Pre-Calculus",
            "description": "Trigonometry, exponential / logarithmic functions, and conic sections.",
            "prerequisites": ["algebra_intermediate"],
            "next": ["calculus_limits"],
        },
        "calculus_limits": {
            "label": "Calculus – Limits",
            "description": "Limits, continuity, and the epsilon-delta definition.",
            "prerequisites": ["precalculus"],
            "next": ["calculus_derivatives"],
        },
        "calculus_derivatives": {
            "label": "Calculus – Derivatives",
            "description": "Differentiation rules, chain rule, and applications.",
            "prerequisites": ["calculus_limits"],
            "next": ["calculus_integrals"],
        },
        "calculus_integrals": {
            "label": "Calculus – Integrals",
            "description": "Anti-derivatives, definite integrals, and the fundamental theorem.",
            "prerequisites": ["calculus_derivatives"],
            "next": [],
        },
    }
}


class KnowledgeGraphService:
    """Lightweight JSON-backed knowledge graph for STEM topics."""

    def __init__(self, graph_path: Optional[str] = None) -> None:
        if graph_path and os.path.isfile(graph_path):
            with open(graph_path, "r") as fh:
                data = json.load(fh)
        else:
            data = DEFAULT_GRAPH
        self._graph: dict = data["topics"]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_all_topics(self) -> list[dict]:
        """Return a list of all topics with metadata."""
        return [
            {
                "id": topic_id,
                "label": info["label"],
                "description": info["description"],
                "prerequisites": info["prerequisites"],
                "next": info["next"],
            }
            for topic_id, info in self._graph.items()
        ]

    def get_topic(self, topic_id: str) -> Optional[dict]:
        """Return a single topic or None if not found."""
        info = self._graph.get(topic_id)
        if info is None:
            return None
        return {
            "id": topic_id,
            "label": info["label"],
            "description": info["description"],
            "prerequisites": info["prerequisites"],
            "next": info["next"],
        }

    def get_next_topic(self, current_topic: str) -> Optional[str]:
        """Return the ID of the next topic after *current_topic*, or None."""
        info = self._graph.get(current_topic)
        if info and info["next"]:
            return info["next"][0]
        return None

    def get_prerequisites(self, topic_id: str) -> list[str]:
        """Return prerequisite topic IDs for *topic_id*."""
        info = self._graph.get(topic_id)
        return info["prerequisites"] if info else []

    def get_entry_topics(self) -> list[str]:
        """Return topics that have no prerequisites (entry points)."""
        return [tid for tid, info in self._graph.items() if not info["prerequisites"]]

    def prerequisites_met(self, topic_id: str, mastered: set[str]) -> bool:
        """Return True if all prerequisites for *topic_id* are in *mastered*."""
        return all(p in mastered for p in self.get_prerequisites(topic_id))
