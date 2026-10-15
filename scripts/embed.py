import json
from pathlib import Path
import sys

import faiss
import numpy as np

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.config import (
    COURSES_JSON_PATH,
    EMBEDDINGS_PATH,
    FAISS_INDEX_PATH,
    INDEX_DIR,
    INDEX_METADATA_PATH,
    MODEL_NAME,
)
from backend.app.search import course_text


def ensure_index_dir() -> None:
    INDEX_DIR.mkdir(parents=True, exist_ok=True)


def load_courses() -> list[dict]:
    if not COURSES_JSON_PATH.exists():
        raise FileNotFoundError("courses.json not found. Run scripts/scrape.py first.")
    return json.loads(COURSES_JSON_PATH.read_text(encoding="utf-8"))


def deduplicate(courses: list[dict]) -> list[dict]:
    """Keep one record per course code (the catalog can list a course under several pages)."""
    seen: set[str] = set()
    unique: list[dict] = []
    for course in courses:
        code = " ".join((course.get("code") or "").upper().split())
        if not code or code in seen:
            continue
        seen.add(code)
        unique.append(course)
    return unique


def main() -> None:
    ensure_index_dir()
    raw_courses = load_courses()
    courses = deduplicate(raw_courses)
    if len(courses) != len(raw_courses):
        print(f"Removed {len(raw_courses) - len(courses)} duplicate course records.")
    texts = [course_text(course) for course in courses]

    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(MODEL_NAME)
    embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=True, normalize_embeddings=True)
    embeddings = np.asarray(embeddings, dtype="float32")

    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)

    np.save(EMBEDDINGS_PATH, embeddings)
    faiss.write_index(index, str(FAISS_INDEX_PATH))
    INDEX_METADATA_PATH.write_text(json.dumps(courses, indent=2, ensure_ascii=True), encoding="utf-8")

    print(f"Embedded {len(courses)} courses with {MODEL_NAME}.")
    print(f"Embeddings saved to {EMBEDDINGS_PATH}")
    print(f"FAISS index saved to {FAISS_INDEX_PATH}")


if __name__ == "__main__":
    main()
