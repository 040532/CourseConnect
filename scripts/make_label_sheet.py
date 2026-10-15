"""Build the relevance-labeling sheet for the evaluation set.

For every query in eval/queries.txt, pool the top results from each retrieval mode
(so no approach is favoured), and write them to eval/labels.csv with an empty
`relevant` column. Open the CSV, mark each row 1 (relevant) or 0 (not relevant),
then run scripts/evaluate.py.

Re-running keeps labels you have already filled in.
"""

import argparse
import csv
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.config import EVAL_DIR, EVAL_LABELS_PATH, EVAL_QUERIES_PATH
from backend.app.search import semantic_search_service

POOL_MODES = ("dense", "bm25", "hybrid", "legacy")


def read_queries(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]


def read_existing_labels(path: Path) -> dict[tuple[str, str], str]:
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8") as handle:
        return {(row["query"], row["code"]): row.get("relevant", "") for row in csv.DictReader(handle)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--depth", type=int, default=10, help="Results pooled per mode per query.")
    args = parser.parse_args()

    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    queries = read_queries(EVAL_QUERIES_PATH)
    existing = read_existing_labels(EVAL_LABELS_PATH)
    artifacts = semantic_search_service.load()

    rows = []
    for query in queries:
        pooled: list[int] = []
        for mode in POOL_MODES:
            ranked, _, _ = semantic_search_service.rank(query, mode=mode, top_k=args.depth)
            pooled.extend(doc_id for doc_id in ranked if doc_id not in pooled)
        for doc_id in pooled:
            course = artifacts.metadata[doc_id]
            key = (query, course["code"])
            rows.append({
                "query": query,
                "code": course["code"],
                "title": course["title"],
                "relevant": existing.get(key, ""),
                "description": course["description"][:300],
            })

    with EVAL_LABELS_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["query", "code", "title", "relevant", "description"])
        writer.writeheader()
        writer.writerows(rows)

    unlabeled = sum(1 for row in rows if row["relevant"] == "")
    print(f"Wrote {len(rows)} rows for {len(queries)} queries to {EVAL_LABELS_PATH} ({unlabeled} still need a 1/0 label).")


if __name__ == "__main__":
    main()
