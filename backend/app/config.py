from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"
INDEX_DIR = DATA_DIR / "index"

DATABASE_URL = f"sqlite:///{(PROCESSED_DIR / 'courseconnect.db').as_posix()}"
MODEL_NAME = "sentence-transformers/all-mpnet-base-v2"
CATALOG_ROOT_URL = "https://catalog.tamu.edu"
CATALOG_INDEX_URL = f"{CATALOG_ROOT_URL}/graduate/course-descriptions/"

COURSES_JSON_PATH = PROCESSED_DIR / "courses.json"
COURSES_CSV_PATH = PROCESSED_DIR / "courses.csv"
EMBEDDINGS_PATH = INDEX_DIR / "course_embeddings.npy"
FAISS_INDEX_PATH = INDEX_DIR / "course_index.faiss"
INDEX_METADATA_PATH = INDEX_DIR / "course_metadata.json"

# --- Retrieval settings -------------------------------------------------------
# Reciprocal Rank Fusion constant (60 is the standard value from Cormack et al., 2009).
RRF_K = 60
# Below this cosine similarity, no result is considered a real match.
MIN_DENSE_SIMILARITY = 0.30
# Cross-encoder used by mode="hybrid_rerank" and how many fused candidates it rescores.
RERANKER_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"
RERANK_CANDIDATES = 30

# --- Evaluation ---------------------------------------------------------------
EVAL_DIR = DATA_DIR.parent / "eval"
EVAL_QUERIES_PATH = EVAL_DIR / "queries.txt"
EVAL_LABELS_PATH = EVAL_DIR / "labels.csv"
