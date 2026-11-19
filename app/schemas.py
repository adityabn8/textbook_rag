from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=3, description="The exam question to ask")
    marks: int = Field(2, ge=1, le=10, description="Marks allotted (e.g., 1, 2, 3, 5)")
    question_type: Literal["objective", "subjective"] = Field(
        "subjective",
        description="Whether the question is objective (MCQ/1-word) or subjective (short/long answer)",
    )
    chapter: Optional[str] = Field(
        None, description="Optional PDF filename filter, e.g., jeff107.pdf"
    )


class SourceChunk(BaseModel):
    file_name: str
    score: float
    text_preview: str


class QueryResponse(BaseModel):
    question: str
    answer: str
    sources: List[SourceChunk]

class ChaptersResponse(BaseModel):
    chapters: List[str]