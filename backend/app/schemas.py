from typing import Optional

from pydantic import BaseModel


class CourseBase(BaseModel):
    code: str
    title: str
    credits: Optional[str] = None
    description: str
    prerequisites: Optional[str] = None


class CourseResponse(CourseBase):
    id: int
    department: str

    class Config:
        from_attributes = True


class SearchResult(CourseBase):
    department: str
    score: float


class SearchResponse(BaseModel):
    results: list[SearchResult]
    returned_count: int
    max_results: int
    applied_threshold: float
    top_score: Optional[float] = None
    message: str
