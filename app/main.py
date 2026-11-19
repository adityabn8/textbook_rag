import os
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google.genai.errors import ClientError, ServerError

from app.rag_engine import TextbookRAG
from app.schemas import QueryRequest, QueryResponse
from app.schemas import ChaptersResponse, QueryRequest, QueryResponse
from fastapi.staticfiles import StaticFiles

rag_engine: TextbookRAG | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global rag_engine
    # Runs ONCE when server starts
    rag_engine = TextbookRAG(qdrant_path="./qdrant_db")
    yield
    # Runs ONCE when server shuts down (releases Qdrant file lock)
    if rag_engine:
        rag_engine.close()


app = FastAPI(
    title="Textbook Exam RAG API",
    description="Hybrid Qdrant + Gemini API for answering textbook exam questions",
    version="1.0.0",
    lifespan=lifespan,
)

# Allow any frontend (HTML, React, Streamlit) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.post("/api/v1/query", response_model=QueryResponse)
def query_textbook(payload: QueryRequest):
    if not rag_engine:
        raise HTTPException(status_code=503, detail="RAG engine not initialized.")

    try:
        result = rag_engine.ask(
            question=payload.question,
            marks=payload.marks,
            question_type=payload.question_type,
            chapter=payload.chapter,
        )

        return result
    except (ServerError, ClientError) as e:
        raise HTTPException(status_code=502, detail=f"Gemini API error: {e.message}")


@app.get("/api/v1/chapters", response_model=ChaptersResponse)
def list_chapters():
    if not rag_engine:
        raise HTTPException(status_code=503, detail="RAG engine not initialized.")

    return {"chapters": rag_engine.get_chapters()}

# 3. Frontend mount MUST go at the very bottom
FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.exists(FRONTEND_DIST):
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
