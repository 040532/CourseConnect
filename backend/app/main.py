from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .db import Base, engine, get_db
from .models import Course
from .schemas import CourseResponse, SearchResult
from .search import infer_department, semantic_search_service


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="CourseConnect API",
    description="Semantic graduate course search backed by Sentence-BERT and FAISS.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "database_ready": engine is not None,
        "semantic_index_ready": semantic_search_service.is_ready(),
    }


@app.get("/courses", response_model=list[CourseResponse])
def get_courses(db: Session = Depends(get_db)):
    courses = db.query(Course).order_by(Course.code.asc()).all()
    response = []
    for course in courses:
        response.append(
            CourseResponse(
                id=course.id,
                code=course.code,
                title=course.title,
                credits=course.credits,
                description=course.description,
                prerequisites=course.prerequisites,
                department=infer_department(course.code),
            )
        )
    return response


@app.get("/search", response_model=list[SearchResult])
def search_courses(
    q: str = Query(..., min_length=2),
    top_k: int = Query(10, ge=1, le=25),
    department: Optional[str] = Query(None),
    min_credits: Optional[float] = Query(None, ge=0),
    max_credits: Optional[float] = Query(None, ge=0),
):
    if not semantic_search_service.is_ready():
        raise HTTPException(
            status_code=503,
            detail="Semantic index is not ready. Run scripts/scrape.py and scripts/embed.py first.",
        )

    results = semantic_search_service.search(
        query=q,
        top_k=top_k,
        department=department,
        min_credits=min_credits,
        max_credits=max_credits,
    )
    return results
