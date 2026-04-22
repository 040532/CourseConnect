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
