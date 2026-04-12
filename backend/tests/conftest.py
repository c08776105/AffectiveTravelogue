"""
Shared fixtures and patches for the test suite.

Strategy for module-level singletons
--------------------------------------
Each service module (rag_service, neo4j_service, eval_service) creates a
singleton instance at import time.  To avoid hitting real infrastructure
(Ollama, Neo4j, Open-Elevation, OSM) during unit tests, we patch the
heavyweight constructors *before* the modules are imported for the first
time, using session-scoped autouse fixtures where needed.

Individual test fixtures then instantiate a fresh class instance on top of
the already-patched environment so they get clean, isolated state.
"""

import json
from unittest.mock import MagicMock, patch

import pytest
import torch


# ---------------------------------------------------------------------------
# Tensor helpers
# ---------------------------------------------------------------------------

def make_score_tensors(p_vals: list[float], r_vals: list[float], f1_vals: list[float]):
    """Return (P, R, F1) as float32 tensors suitable for BERTScorer.score()."""
    return (
        torch.tensor(p_vals, dtype=torch.float32),
        torch.tensor(r_vals, dtype=torch.float32),
        torch.tensor(f1_vals, dtype=torch.float32),
    )


def make_mock_scorer(
    p_vals: list[float],
    r_vals: list[float],
    f1_vals: list[float],
    token_lengths: list[int] | None = None,
) -> MagicMock:
    """
    Build a mock BERTScorer that returns predefined scores.

    token_lengths: list of encode() return lengths for each call, in order.
    If None, every encode() call returns a 3-token list (well under 512).
    """
    scorer = MagicMock()
    tok = MagicMock()
    tok.model_max_length = 512

    if token_lengths is None:
        tok.encode.return_value = [1, 2, 3]  # 3 tokens — never truncated
    else:
        tok.encode.side_effect = [list(range(n)) for n in token_lengths]

    scorer._tokenizer = tok
    scorer.score.return_value = make_score_tensors(p_vals, r_vals, f1_vals)
    return scorer


# ---------------------------------------------------------------------------
# EvaluationService fixture
# ---------------------------------------------------------------------------

@pytest.fixture()
def eval_svc():
    """Fresh EvaluationService instance.  Scorer is NOT loaded; tests inject it."""
    from services.eval_service import EvaluationService
    return EvaluationService()


# ---------------------------------------------------------------------------
# Neo4jService fixture
# ---------------------------------------------------------------------------

@pytest.fixture()
def neo4j_svc(mocker):
    """
    Neo4jService with the Neo4j driver replaced by a MagicMock.
    Each test that opens a session will receive a mock session context manager.
    """
    mocker.patch("neo4j.GraphDatabase.driver", return_value=MagicMock())
    from services.neo4j_service import Neo4jService
    svc = Neo4jService()
    svc.driver = MagicMock()
    return svc


def make_session_mock(records: list[dict] | None = None) -> MagicMock:
    """
    Helper: build a mock Neo4j session context manager whose run().single()
    returns the first record dict (or None), and whose run() is iterable
    over all records.
    """
    session = MagicMock()
    result = MagicMock()

    single_val = records[0] if records else None
    result.single.return_value = single_val
    result.__iter__ = lambda self: iter(records or [])

    session.run.return_value = result
    ctx = MagicMock()
    ctx.__enter__ = lambda s: session
    ctx.__exit__ = MagicMock(return_value=False)
    return ctx, session


# ---------------------------------------------------------------------------
# RAGService fixture
# ---------------------------------------------------------------------------

@pytest.fixture()
def rag_svc(mocker):
    """
    RAGService with OllamaLLM and system_prompt.txt both mocked out.
    Returns (service, mock_llm) so tests can configure llm.invoke() etc.
    """
    mock_llm_instance = MagicMock()
    mocker.patch(
        "services.rag_service.OllamaLLM",
        return_value=mock_llm_instance,
    )
    mocker.patch(
        "builtins.open",
        mocker.mock_open(read_data="You are a walk narrator. Write one paragraph per waypoint."),
    )
    from services.rag_service import RAGService
    svc = RAGService()
    return svc, mock_llm_instance


# ---------------------------------------------------------------------------
# Shared waypoint / POI test data
# ---------------------------------------------------------------------------

WAYPOINTS = [
    {"id": "wp-1", "latitude": 53.249, "longitude": -6.589, "text_note": "We begin our walk."},
    {"id": "wp-2", "latitude": 53.248, "longitude": -6.591, "text_note": json.dumps({"text": "We cross a bridge."})},
    {"id": "wp-3", "latitude": 53.247, "longitude": -6.593, "text_note": None},
]

POI_MAP: dict[int, list[dict]] = {
    0: [
        {"name": "Kill River", "type": "waterway:river", "salience": "HIGH"},
        {"name": "unnamed", "type": "amenity:waste_basket", "salience": "LOW"},
    ],
    1: [
        {"name": "The Old House", "type": "amenity:pub", "salience": "HIGH"},
        {"name": "unnamed", "type": "amenity:parking", "salience": "MEDIUM"},
    ],
    2: [],
}

ELEVATIONS: list[float] = [45.0, 57.0, 50.0]
