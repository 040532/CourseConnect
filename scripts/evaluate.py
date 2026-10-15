"""Evaluate retrieval quality on the hand-labeled query set.

Reads eval/labels.csv (rows marked relevant=1/0), runs every retrieval mode, and
reports standard IR metrics:

  P@5      precision at 5: share of the top 5 results that are relevant
  R@10     recall at 10: share of all known relevant courses found in the top 10
  MRR@10   mean reciprocal rank of the first relevant result
  nDCG@10  normalized discounted cumulative gain (rewards relevant results ranked higher)

Courses that were never labeled count as not relevant (standard pooled evaluation).
Writes a Markdown summary to eval/results.md and per-query scores to eval/per_query.csv.
"""

import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path
import sys
import time

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.config import EVAL_DIR, EVAL_LABELS_PATH
from backend.app.search import semantic_search_service

DEFAULT_MODES = ["legacy", "dense", "bm25", "hybrid"]


def load_labels(path: Path) -> dict[str, set[str]]:
    relevant: dict[str, set[str]] = defaultdict(set)
    labeled_queries: set[str] = set()
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            value = (row.get("relevant") or "").strip()
            if value not in {"0", "1"}:
                continue
            labeled_queries.add(row["query"])
            if value == "1":
                relevant[row["query"]].add(row["code"])
    return {query: relevant[query] for query in labeled_queries if relevant[query]}


def precision_at(ranked: list[str], relevant: set[str], k: int) -> float:
    return sum(code in relevant for code in ranked[:k]) / k


def recall_at(ranked: list[str], relevant: set[str], k: int) -> float:
    return sum(code in relevant for code in ranked[:k]) / len(relevant)


def mrr_at(ranked: list[str], relevant: set[str], k: int) -> float:
    for position, code in enumerate(ranked[:k], start=1):
        if code in relevant:
            return 1.0 / position
    return 0.0


def ndcg_at(ranked: list[str], relevant: set[str], k: int) -> float:
    dcg = sum(1.0 / math.log2(position + 1) for position, code in enumerate(ranked[:k], start=1) if code in relevant)
    ideal = sum(1.0 / math.log2(position + 1) for position in range(1, min(len(relevant), k) + 1))
    return dcg / ideal if ideal else 0.0


METRICS = {
    "P@5": lambda r, rel: precision_at(r, rel, 5),
    "R@10": lambda r, rel: recall_at(r, rel, 10),
    "MRR@10": lambda r, rel: mrr_at(r, rel, 10),
    "nDCG@10": lambda r, rel: ndcg_at(r, rel, 10),
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--modes", nargs="+", default=DEFAULT_MODES,
                        help="Modes to compare (add hybrid_rerank to test the cross-encoder).")
    args = parser.parse_args()

    labels = load_labels(EVAL_LABELS_PATH)
    if not labels:
        raise SystemExit(f"No labeled queries found in {EVAL_LABELS_PATH}. Run scripts/make_label_sheet.py and fill in the 'relevant' column.")

    artifacts = semantic_search_service.load()
    summary: dict[str, dict[str, float]] = {}
    per_query_rows = []

    for mode in args.modes:
        totals = defaultdict(float)
        start = time.perf_counter()
        for query, relevant in labels.items():
            ranked_ids, _, _ = semantic_search_service.rank(query, mode=mode, top_k=10)
            ranked = [artifacts.metadata[doc_id]["code"] for doc_id in ranked_ids]
            row = {"mode": mode, "query": query}
            for name, metric in METRICS.items():
                value = metric(ranked, relevant)
                totals[name] += value
                row[name] = round(value, 3)
            per_query_rows.append(row)
        elapsed_ms = (time.perf_counter() - start) * 1000 / len(labels)
        summary[mode] = {name: totals[name] / len(labels) for name in METRICS}
        summary[mode]["ms/query"] = elapsed_ms

    headers = ["Mode", *METRICS.keys(), "ms/query"]
    lines = [
        f"Evaluated on {len(labels)} labeled queries ({sum(len(v) for v in labels.values())} relevant judgments).",
        "",
        "| " + " | ".join(headers) + " |",
        "|" + "---|" * len(headers),
    ]
    for mode, values in summary.items():
        cells = [mode] + [f"{values[name]:.3f}" for name in METRICS] + [f"{values['ms/query']:.0f}"]
        lines.append("| " + " | ".join(cells) + " |")
    report = "\n".join(lines)
    print(report)

    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    (EVAL_DIR / "results.md").write_text(report + "\n", encoding="utf-8")
    with (EVAL_DIR / "per_query.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["mode", "query", *METRICS.keys()])
        writer.writeheader()
        writer.writerows(per_query_rows)
    print(f"\nSaved {EVAL_DIR / 'results.md'} and {EVAL_DIR / 'per_query.csv'}")


if __name__ == "__main__":
    main()
