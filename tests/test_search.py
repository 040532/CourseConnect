"""Unit tests for retrieval logic, using a tiny fake encoder (no model download)."""

import hashlib
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.search import (  # noqa: E402
    SemanticSearchService,
    build_artifacts,
    course_text,
    lexical_query,
    reciprocal_rank_fusion,
    strip_filler,
    tokenize,
)
from scripts.embed import deduplicate  # noqa: E402

DIM = 64


def fake_encode(texts):
    """Hashed bag-of-words vectors: similar wording -> similar vectors."""
    vectors = np.zeros((len(texts), DIM), dtype="float32")
    for row, text in enumerate(texts):
        for token in tokenize(text):
            vectors[row, int(hashlib.md5(token.encode()).hexdigest(), 16) % DIM] += 1.0
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    return vectors / np.where(norms == 0, 1, norms)


COURSES = [
    {"code": "CSCE 633", "title": "Machine Learning", "credits": "3", "description": "Supervised learning, neural networks, and deep learning methods."},
    {"code": "CSCE 662", "title": "Distributed Processing Systems", "credits": "3", "description": "Distributed systems, cloud computing, consistency, and fault tolerance."},
    {"code": "STAT 651", "title": "Statistics in Research", "credits": "4", "description": "Statistical methods for public health and biological research."},
    {"code": "ANSC 605", "title": "Animal Nutrition", "credits": "3", "description": "Nutrient metabolism and feeding of livestock and companion animals."},
    {"code": "CSCE 634", "title": "Intelligent Systems Design", "credits": "3", "description": "Artificial intelligence planning, robotics, and autonomous agents."},
]


@pytest.fixture()
def service():
    embeddings = fake_encode([course_text(c) for c in COURSES])
    return SemanticSearchService(build_artifacts(fake_encode, embeddings, COURSES))


def test_strip_filler_keeps_topic_words():
    assert strip_filler("What courses should I take for distributed systems?") == "for distributed systems"


def test_expansions_only_affect_lexical_query():
    tokens = lexical_query("ai")
    assert "artificial" in tokens and "intelligence" in tokens


def test_rrf_rewards_agreement():
    fused = reciprocal_rank_fusion([[1, 2, 3], [2, 1, 4]], k=60)
    assert fused[1] == pytest.approx(fused[2])
    assert fused[1] > fused[3] > 0 and fused[1] > fused[4]


@pytest.mark.parametrize("mode", ["dense", "bm25", "hybrid", "legacy"])
def test_modes_find_obvious_match(service, mode):
    ranked, scores, _ = service.rank("distributed systems cloud computing", mode=mode, top_k=3)
    assert COURSES[ranked[0]]["code"] == "CSCE 662"
    assert all(0 <= scores[d] <= 100.0001 for d in ranked)


def test_filters_apply_before_ranking(service):
    ranked, _, _ = service.rank("machine learning", mode="hybrid", top_k=5, department="ANSC")
    assert [COURSES[d]["code"] for d in ranked] == ["ANSC 605"]


def test_credit_filter(service):
    ranked, _, _ = service.rank("statistics", mode="hybrid", top_k=5, min_credits=4)
    assert {COURSES[d]["code"] for d in ranked} == {"STAT 651"}


def test_search_response_shape(service):
    response = service.search("machine learning neural networks", top_k=3)
    assert response["returned_count"] == len(response["results"]) <= 3
    assert response["results"][0]["code"] == "CSCE 633"
    assert {"department", "score", "code", "title"} <= response["results"][0].keys()


def test_deduplicate_by_code():
    courses = [{"code": "CSCE 633"}, {"code": "csce  633"}, {"code": "CSCE 662"}]
    assert [c["code"] for c in deduplicate(courses)] == ["CSCE 633", "CSCE 662"]
