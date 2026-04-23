import json
import os
import re
from dataclasses import dataclass
from typing import Any, Optional

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("VECLIB_MAXIMUM_THREADS", "1")

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from .config import EMBEDDINGS_PATH, FAISS_INDEX_PATH, INDEX_METADATA_PATH, MODEL_NAME

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
    "a",
    "about",
    "an",
    "and",
    "are",
    "class",
    "classes",
    "course",
    "courses",
    "for",
    "find",
    "help",
    "helpful",
    "i",
    "in",
    "into",
    "is",
    "like",
    "me",
    "my",
    "of",
    "on",
    "please",
    "recommend",
    "related",
    "should",
    "take",
    "that",
    "the",
    "to",
    "want",
    "what",
    "which",
    "with",
    "work",
    "would",
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


def infer_department(code: str) -> str:
    match = re.match(r"([A-Z&]+)", code or "")
    return match.group(1) if match else "Other"


def parse_credit_value(credits: Optional[str]) -> Optional[float]:
    if not credits:
        return None
    match = re.search(r"(\d+(?:\.\d+)?)", credits)
    return float(match.group(1)) if match else None


def query_terms(query: str) -> list[str]:
    terms = re.findall(r"[A-Za-z0-9]+", query.lower())
    return [term for term in terms if len(term) > 2 and term not in QUERY_STOPWORDS]


def normalize_query(query: str) -> str:
    normalized = query.lower()
    normalized = re.sub(r"[?.!,;:]", " ", normalized)

    for phrase in QUERY_FILLER_PHRASES:
        normalized = re.sub(rf"\b{re.escape(phrase)}\b", " ", normalized)

    expansions: list[str] = []
    for phrase, expansion in PHRASE_EXPANSIONS.items():
        if re.search(rf"\b{re.escape(phrase)}\b", normalized):
            expansions.append(expansion)

    terms = query_terms(normalized)
    for term in terms:
        if term in DOMAIN_EXPANSIONS:
            expansions.append(DOMAIN_EXPANSIONS[term])

    cleaned = " ".join(terms + expansions)
    return cleaned or query


@dataclass
class SearchArtifacts:
    model: SentenceTransformer
    index: Any
    metadata: list[dict[str, Any]]


class SemanticSearchService:
    def __init__(self) -> None:
        self._artifacts: Optional[SearchArtifacts] = None

    def is_ready(self) -> bool:
        return FAISS_INDEX_PATH.exists() and INDEX_METADATA_PATH.exists() and EMBEDDINGS_PATH.exists()

    def load(self) -> SearchArtifacts:
        if self._artifacts is None:
            model = SentenceTransformer(MODEL_NAME)
            index = faiss.read_index(str(FAISS_INDEX_PATH))
            metadata = json.loads(INDEX_METADATA_PATH.read_text(encoding="utf-8"))
            self._artifacts = SearchArtifacts(model=model, index=index, metadata=metadata)
        return self._artifacts

    def search(
        self,
        query: str,
        top_k: int = 10,
        department: Optional[str] = None,
        min_credits: Optional[float] = None,
        max_credits: Optional[float] = None,
    ) -> dict[str, Any]:
        artifacts = self.load()
        search_query = normalize_query(query)
        query_embedding = artifacts.model.encode([search_query], convert_to_numpy=True, normalize_embeddings=True)

        # Search a wider candidate pool first so filters do not starve the result set.
        search_k = min(max(top_k * 5, 25), len(artifacts.metadata))
        scores, indices = artifacts.index.search(np.asarray(query_embedding, dtype="float32"), search_k)

        normalized_department = department.upper() if department else None
        candidates: list[dict[str, Any]] = []
        meaningful_query_terms = query_terms(search_query)

        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue
            item = dict(artifacts.metadata[idx])
            item_department = infer_department(item.get("code", ""))
            credits_value = parse_credit_value(item.get("credits"))

            if normalized_department and item_department != normalized_department:
                continue
            if min_credits is not None and (credits_value is None or credits_value < min_credits):
                continue
            if max_credits is not None and (credits_value is None or credits_value > max_credits):
                continue

            combined_text = f"{item.get('title', '')} {item.get('description', '')}".lower()
            keyword_overlap = sum(term in combined_text for term in meaningful_query_terms)
            blended_score = float(score)
            if meaningful_query_terms:
                blended_score += min(keyword_overlap / max(len(meaningful_query_terms), 1), 1.0) * 0.08

            item.update(
                {
                    "department": item_department,
                    "score": round(max(0.0, min(blended_score, 1.0)) * 100, 2),
                }
            )
            candidates.append(item)

        ranked = sorted(candidates, key=lambda result: result["score"], reverse=True)
        if not ranked:
            return {
                "results": [],
                "returned_count": 0,
                "max_results": top_k,
                "applied_threshold": 0.0,
                "top_score": None,
                "message": "No courses matched the current query and filter combination.",
            }

        top_score = ranked[0]["score"]
        applied_threshold = round(max(58.0, top_score - 14.0), 2)

        if top_score < 52.0:
            return {
                "results": [],
                "returned_count": 0,
                "max_results": top_k,
                "applied_threshold": applied_threshold,
                "top_score": top_score,
                "message": "No sufficiently aligned courses were found. Try broadening the query or removing a filter.",
            }

        results = [item for item in ranked if item["score"] >= applied_threshold][:top_k]

        return {
            "results": results,
            "returned_count": len(results),
            "max_results": top_k,
            "applied_threshold": applied_threshold,
            "top_score": top_score,
            "message": f"Showing {len(results)} high-confidence matches out of a maximum of {top_k}.",
        }


semantic_search_service = SemanticSearchService()
