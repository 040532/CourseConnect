import json
from pathlib import Path
import sys

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

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


def ensure_index_dir() -> None:
    INDEX_DIR.mkdir(parents=True, exist_ok=True)


def load_courses() -> list[dict]:
    if not COURSES_JSON_PATH.exists():
        raise FileNotFoundError("courses.json not found. Run scripts/scrape.py first.")
    return json.loads(COURSES_JSON_PATH.read_text(encoding="utf-8"))


def combined_text(course: dict) -> str:
    return f"{course['title']}. {course['description']}"


def main() -> None:
    ensure_index_dir()
    courses = load_courses()
    texts = [combined_text(course) for course in courses]

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
