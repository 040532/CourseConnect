"""Course retrieval for CourseConnect.

Retrieval pipeline (mode="hybrid", the default):

1. Query cleanup     - strip conversational filler ("what courses should I take ...").
2. Dense retrieval   - embed the *cleaned* query (no keyword expansion, so the
                       query vector keeps its meaning) and score every candidate
                       course by cosine similarity.
3. Lexical retrieval - BM25 over code + title + description, using the cleaned
                       query plus domain-specific expansions ("ai" -> "artificial
                       intelligence machine learning ..."). Expansions help keyword
                       recall without diluting the dense query vector.
4. Fusion            - Reciprocal Rank Fusion (RRF) merges the two ranked lists.
                       RRF only uses ranks, so dense and BM25 scores never need to
                       be put on the same scale.
5. Rerank (optional) - mode="hybrid_rerank" rescores the fused top candidates with
                       a cross-encoder that reads query and course text together.

Filters (department, credits) are applied *before* ranking, so a narrow filter can
never starve the result list.

Other modes ("dense", "bm25", "legacy") exist so scripts/evaluate.py can compare
approaches on the same labeled queries. "legacy" reproduces the original
search behaviour (expanded query embedded + substring keyword bonus).
"""

import json
import os
import re
from dataclasses import dataclass
from typing import Any, Callable, Optional, Sequence

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("VECLIB_MAXIMUM_THREADS", "1")

import faiss
import numpy as np
from rank_bm25 import BM25Okapi

from .config import (
    EMBEDDINGS_PATH,
    FAISS_INDEX_PATH,
    INDEX_METADATA_PATH,
    MIN_DENSE_SIMILARITY,
    MODEL_NAME,
    RERANK_CANDIDATES,
    RERANKER_MODEL_NAME,
    RRF_K,
)

SEARCH_MODES = ("hybrid", "hybrid_rerank", "dense", "bm25", "legacy")

QUERY_FILLER_PHRASES = [
    "what course would help me",
    "what courses would help me",
    "what course should i take",
    "what courses should i take",
    "can you recommend",
    "could you recommend",
    "please recommend",
    "recommend me",
    "i am interested in",
    "i'm interested in",
    "i want to work on",
    "i want to learn about",
    "i would like to learn",
    "i like",
    "courses related to",
    "course related to",
    "classes related to",
    "class related to",
    "help me find",
    "for me",
]

QUERY_STOPWORDS = {
    "a", "about", "an", "and", "are", "class", "classes", "course", "courses", "for",
    "find", "help", "helpful", "i", "in", "into", "is", "like", "me", "my", "of", "on",
    "please", "recommend", "related", "should", "take", "that", "the", "to", "want",
    "what", "which", "with", "work", "would",
}

DOMAIN_EXPANSIONS = {
    "ai": "artificial intelligence machine learning deep learning",
    "analytics": "data analytics data mining statistical modeling",
    "biology": "computational biology bioinformatics genomics biomedical",
    "biomedical": "healthcare medicine clinical health bioinformatics",
    "cloud": "distributed systems cloud computing scalable systems",
    "cybersecurity": "security privacy cryptography network security",
    "data": "data science data mining analytics databases",
    "genomics": "computational biology bioinformatics genetics biomedical",
    "health": "healthcare biomedical medicine clinical public health health informatics",
    "healthcare": "health biomedical medicine clinical public health health informatics",
    "machine": "machine learning artificial intelligence data mining",
    "medicine": "healthcare biomedical clinical public health",
    "privacy": "privacy security cybersecurity data protection",
    "robotics": "robotics autonomous systems intelligent systems control",
    "security": "cybersecurity privacy cryptography network security",
    "vision": "computer vision image processing deep learning",
}

PHRASE_EXPANSIONS = {
    "machine learning": "machine learning artificial intelligence deep learning data mining",
    "public health": "public health healthcare health informatics epidemiology",
    "computer vision": "computer vision image processing visual recognition deep learning",
    "data science": "data science data mining analytics machine learning",
}

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

def infer_department(code: str) -> str:
    match = re.match(r"([A-Z&]+)", code or "")
    return match.group(1) if match else "Other"


def parse_credit_value(credits: Optional[str]) -> Optional[float]:
    if not credits:
        return None
    match = re.search(r"(\d+(?:\.\d+)?)", credits)
    return float(match.group(1)) if match else None


def tokenize(text: str) -> list[str]:
    return TOKEN_PATTERN.findall((text or "").lower())


def query_terms(query: str) -> list[str]:
    return [term for term in tokenize(query) if len(term) > 2 and term not in QUERY_STOPWORDS]


def strip_filler(query: str) -> str:
    """Remove conversational filler while keeping the user's actual topic words."""
    cleaned = query.lower()
    cleaned = re.sub(r"[?.!,;:]", " ", cleaned)
    for phrase in QUERY_FILLER_PHRASES:
        cleaned = re.sub(rf"\b{re.escape(phrase)}\b", " ", cleaned)
    cleaned = " ".join(cleaned.split())
    return cleaned or query.strip()


def expansions_for(cleaned_query: str) -> list[str]:
    expansions: list[str] = []
    for phrase, expansion in PHRASE_EXPANSIONS.items():
        if re.search(rf"\b{re.escape(phrase)}\b", cleaned_query):
            expansions.append(expansion)
    # Check every token, not just query_terms(): short keys such as "ai" would
    # otherwise be dropped by the length filter and never expanded.
    for term in dict.fromkeys(tokenize(cleaned_query)):
        if term in DOMAIN_EXPANSIONS:
            expansions.append(DOMAIN_EXPANSIONS[term])
    return expansions


def lexical_query(cleaned_query: str) -> list[str]:
    """BM25 query tokens: topic words plus domain expansions."""
    tokens = query_terms(cleaned_query) + [t for t in tokenize(cleaned_query) if t in DOMAIN_EXPANSIONS]
    for expansion in expansions_for(cleaned_query):
        tokens.extend(query_terms(expansion))
    return tokens


def legacy_normalize_query(query: str) -> str:
    """Original query rewrite (filler removal + expansions), kept for the 'legacy' baseline."""
    cleaned = strip_filler(query)
    terms = query_terms(cleaned)
    expansions = [e for p, e in PHRASE_EXPANSIONS.items() if re.search(rf"\b{re.escape(p)}\b", cleaned)]
    expansions += [DOMAIN_EXPANSIONS[t] for t in terms if t in DOMAIN_EXPANSIONS]  # original behaviour
    cleaned_with_expansions = " ".join(terms + expansions)
    return cleaned_with_expansions or query


def course_text(course: dict) -> str:
    """Text used for both embeddings and BM25. Must match scripts/embed.py."""
    return f"{course.get('code', '')} {course.get('title', '')}. {course.get('description', '')}"


def reciprocal_rank_fusion(ranked_lists: Sequence[Sequence[int]], k: int = RRF_K) -> dict[int, float]:
    """Combine ranked lists of document ids: score(d) = sum over lists of 1 / (k + rank)."""
    fused: dict[int, float] = {}
    for ranked in ranked_lists:
        for rank, doc_id in enumerate(ranked, start=1):
            fused[doc_id] = fused.get(doc_id, 0.0) + 1.0 / (k + rank)
    return fused


# ---------------------------------------------------------------------------
# Search service
# ---------------------------------------------------------------------------

@dataclass
class SearchArtifacts:
    encode: Callable[[list[str]], np.ndarray]  # returns L2-normalized float32 vectors
    embeddings: np.ndarray                      # (n_courses, dim), L2-normalized
    index: Any                                  # FAISS inner-product index over embeddings
    metadata: list[dict[str, Any]]
    bm25: BM25Okapi
    departments: np.ndarray
    credits: np.ndarray                         # float, nan when unknown


def build_artifacts(
    encode: Callable[[list[str]], np.ndarray],
    embeddings: np.ndarray,
    metadata: list[dict[str, Any]],
    index: Any = None,
) -> SearchArtifacts:
    embeddings = np.asarray(embeddings, dtype="float32")
    if len(embeddings) != len(metadata):
        raise ValueError("Embeddings and metadata are out of sync. Re-run scripts/embed.py.")
    if index is None:
        index = faiss.IndexFlatIP(embeddings.shape[1])
        index.add(embeddings)
    bm25 = BM25Okapi([tokenize(course_text(course)) for course in metadata])
    departments = np.array([infer_department(course.get("code", "")) for course in metadata])
    credits = np.array(
        [np.nan if parse_credit_value(course.get("credits")) is None else parse_credit_value(course.get("credits"))
         for course in metadata],
        dtype="float64",
    )
    return SearchArtifacts(encode, embeddings, index, metadata, bm25, departments, credits)


class SemanticSearchService:
    def __init__(self, artifacts: Optional[SearchArtifacts] = None) -> None:
        self._artifacts = artifacts
        self._reranker = None

    # -- loading -----------------------------------------------------------
    def is_ready(self) -> bool:
        if self._artifacts is not None:
            return True
        return INDEX_METADATA_PATH.exists() and EMBEDDINGS_PATH.exists()

    def load(self) -> SearchArtifacts:
        if self._artifacts is None:
            from sentence_transformers import SentenceTransformer

            model = SentenceTransformer(MODEL_NAME)

            def encode(texts: list[str]) -> np.ndarray:
                vectors = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
                return np.asarray(vectors, dtype="float32")

            embeddings = np.load(EMBEDDINGS_PATH)
            metadata = json.loads(INDEX_METADATA_PATH.read_text(encoding="utf-8"))
            index = faiss.read_index(str(FAISS_INDEX_PATH)) if FAISS_INDEX_PATH.exists() else None
            self._artifacts = build_artifacts(encode, embeddings, metadata, index)
        return self._artifacts

    def _rerank_scores(self, query: str, docs: list[dict[str, Any]]) -> np.ndarray:
        if self._reranker is None:
            from sentence_transformers import CrossEncoder

            self._reranker = CrossEncoder(RERANKER_MODEL_NAME)
        pairs = [(query, course_text(doc)) for doc in docs]
        return np.asarray(self._reranker.predict(pairs), dtype="float64")

    # -- ranking -----------------------------------------------------------
    def _candidate_mask(
        self,
        artifacts: SearchArtifacts,
        department: Optional[str],
        min_credits: Optional[float],
        max_credits: Optional[float],
    ) -> np.ndarray:
        mask = np.ones(len(artifacts.metadata), dtype=bool)
        if department:
            mask &= artifacts.departments == department.upper()
        if min_credits is not None:
            mask &= np.nan_to_num(artifacts.credits, nan=-1.0) >= min_credits
        if max_credits is not None:
            mask &= np.nan_to_num(artifacts.credits, nan=np.inf) <= max_credits
        return mask

    @staticmethod
    def _faiss_search(artifacts: SearchArtifacts, query_vector: np.ndarray, candidate_ids: np.ndarray, k: int) -> np.ndarray:
        """FAISS top-k restricted to candidate ids (filters are applied inside the search)."""
        k = min(k, candidate_ids.size)
        query = np.asarray(query_vector, dtype="float32").reshape(1, -1)
        if candidate_ids.size == len(artifacts.metadata):
            _, ids = artifacts.index.search(query, k)
        else:
            selector = faiss.IDSelectorBatch(candidate_ids.astype("int64"))
            _, ids = artifacts.index.search(query, k, params=faiss.SearchParameters(sel=selector))
        return ids[0][ids[0] >= 0]

    def rank(
        self,
        query: str,
        mode: str = "hybrid",
        top_k: int = 10,
        department: Optional[str] = None,
        min_credits: Optional[float] = None,
        max_credits: Optional[float] = None,
        pool_size: int = 100,
    ) -> tuple[list[int], dict[int, float], np.ndarray]:
        """Return (ranked doc ids, display score per doc in 0-100, dense similarity per doc)."""
        if mode not in SEARCH_MODES:
            raise ValueError(f"Unknown mode {mode!r}. Choose one of {SEARCH_MODES}.")
        artifacts = self.load()
        candidate_ids = np.flatnonzero(self._candidate_mask(artifacts, department, min_credits, max_credits))
        if candidate_ids.size == 0:
            return [], {}, np.zeros(len(artifacts.metadata))

        cleaned = strip_filler(query)
        dense_query = legacy_normalize_query(query) if mode == "legacy" else cleaned
        query_vector = artifacts.encode([dense_query])[0]
        dense_all = artifacts.embeddings @ query_vector  # cosine similarity (vectors are normalized)
        dense_order = self._faiss_search(artifacts, query_vector, candidate_ids, max(pool_size, top_k * 5, 25))

        if mode == "dense":
            ranked = dense_order[:top_k].tolist()
            return ranked, {d: float(dense_all[d]) * 100 for d in ranked}, dense_all

        if mode == "legacy":
            terms = query_terms(dense_query)
            scored = []
            for doc_id in dense_order[: max(top_k * 5, 25)]:
                text = course_text(artifacts.metadata[doc_id]).lower()
                overlap = sum(term in text for term in terms)  # original substring matching
                bonus = min(overlap / max(len(terms), 1), 1.0) * 0.08 if terms else 0.0
                scored.append((float(dense_all[doc_id]) + bonus, int(doc_id)))
            scored.sort(reverse=True)
            ranked = [doc_id for _, doc_id in scored[:top_k]]
            return ranked, {doc_id: min(score, 1.0) * 100 for score, doc_id in scored[:top_k]}, dense_all

        bm25_all = np.asarray(artifacts.bm25.get_scores(lexical_query(cleaned)), dtype="float64")
        bm25 = bm25_all[candidate_ids]
        bm25_order = candidate_ids[np.argsort(-bm25)]
        bm25_order = [d for d in bm25_order if bm25_all[d] > 0]  # ignore docs with no term overlap

        if mode == "bm25":
            ranked = [int(d) for d in bm25_order[:top_k]]
            top = bm25_all[ranked[0]] if ranked else 1.0
            return ranked, {d: float(bm25_all[d] / top) * 100 for d in ranked}, dense_all

        fused = reciprocal_rank_fusion([dense_order[:pool_size].tolist(), list(bm25_order[:pool_size])])
        fused_order = sorted(fused, key=fused.get, reverse=True)
        best_possible = 2.0 / (RRF_K + 1)  # rank 1 in both lists

        if mode == "hybrid":
            ranked = [int(d) for d in fused_order[:top_k]]
            return ranked, {d: fused[d] / best_possible * 100 for d in ranked}, dense_all

        # hybrid_rerank
        pool = [int(d) for d in fused_order[:RERANK_CANDIDATES]]
        logits = self._rerank_scores(cleaned, [artifacts.metadata[d] for d in pool])
        order = np.argsort(-logits)
        ranked = [pool[i] for i in order[:top_k]]
        probabilities = 1.0 / (1.0 + np.exp(-logits))
        return ranked, {pool[i]: float(probabilities[i]) * 100 for i in order[:top_k]}, dense_all

    # -- API response --------------------------------------------------------
    def search(
        self,
        query: str,
        top_k: int = 10,
        department: Optional[str] = None,
        min_credits: Optional[float] = None,
        max_credits: Optional[float] = None,
        mode: str = "hybrid",
    ) -> dict[str, Any]:
        artifacts = self.load()
        ranked, scores, dense_all = self.rank(query, mode, top_k, department, min_credits, max_credits)
        threshold = round(MIN_DENSE_SIMILARITY * 100, 2)

        if not ranked:
            return {
                "results": [],
                "returned_count": 0,
                "max_results": top_k,
                "applied_threshold": threshold,
                "top_score": None,
                "message": "No courses matched the current query and filter combination.",
            }

        # Confidence gate: if nothing is even moderately similar in meaning, say so
        # instead of returning keyword-only noise.
        if float(dense_all[ranked].max()) < MIN_DENSE_SIMILARITY:
            return {
                "results": [],
                "returned_count": 0,
                "max_results": top_k,
                "applied_threshold": threshold,
                "top_score": None,
                "message": "No sufficiently aligned courses were found. Try broadening the query or removing a filter.",
            }

        results = []
        for doc_id in ranked:
            item = dict(artifacts.metadata[doc_id])
            item["department"] = infer_department(item.get("code", ""))
            item["score"] = round(max(0.0, min(scores[doc_id], 100.0)), 2)
            results.append(item)

        return {
            "results": results,
            "returned_count": len(results),
            "max_results": top_k,
            "applied_threshold": threshold,
            "top_score": results[0]["score"],
            "message": f"Showing the top {len(results)} matches ({mode} retrieval).",
        }


semantic_search_service = SemanticSearchService()
