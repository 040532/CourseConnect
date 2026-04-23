import json
import re
from dataclasses import dataclass
from typing import Any, Optional

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from .config import EMBEDDINGS_PATH, FAISS_INDEX_PATH, INDEX_METADATA_PATH, MODEL_NAME


def infer_department(code: str) -> str:
    match = re.match(r"([A-Z&]+)", code or "")
    return match.group(1) if match else "Other"


def parse_credit_value(credits: Optional[str]) -> Optional[float]:
    if not credits:
        return None
    match = re.search(r"(\d+(?:\.\d+)?)", credits)
    return float(match.group(1)) if match else None


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
        query_embedding = artifacts.model.encode([query], convert_to_numpy=True, normalize_embeddings=True)

        # Search a wider candidate pool first so filters do not starve the result set.
        search_k = min(max(top_k * 5, 25), len(artifacts.metadata))
        scores, indices = artifacts.index.search(np.asarray(query_embedding, dtype="float32"), search_k)

        normalized_department = department.upper() if department else None
        candidates: list[dict[str, Any]] = []
        query_terms = [term for term in re.findall(r"[A-Za-z0-9]+", query.lower()) if len(term) > 2]

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
            keyword_overlap = sum(term in combined_text for term in query_terms)
            blended_score = float(score)
            if query_terms:
                blended_score += min(keyword_overlap / max(len(query_terms), 1), 1.0) * 0.08

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
