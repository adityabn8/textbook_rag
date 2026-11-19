# NCERT Exam Study Desk — Hybrid RAG Full-Stack Application

A grounded Retrieval-Augmented Generation (RAG) web application built for CBSE/NCERT exam preparation. It combines **Qdrant Hybrid Search** (dense semantic vectors + sparse BM25 keyword matching), **Google Gemini**, **FastAPI**, and a responsive **React (TypeScript + Tailwind CSS)** split-screen study interface.

---

## Key Features

* **Hybrid Search with Reciprocal Rank Fusion (RRF):** Combines `gemini-embedding-001` semantic embeddings with `Qdrant/bm25` sparse keyword vectors to retrieve both conceptual themes and exact names, dates, and definitions.
* **Dynamic Exam-Aware Retrieval Routing:** Automatically adjusts dense retrieval depth (`dense_k`), sparse candidate pool (`sparse_k`), semantic-vs-keyword balance (`alpha`), and CBSE answer formatting based on allotted **Marks (`1M`–`10M`)** and **Question Type (`Objective` vs. `Subjective`)**.
* **Strict Textbook Grounding:** Enforces source citations and refuses to hallucinate answers when topics fall outside the ingested NCERT curriculum.
* **Unified Same-Origin Architecture:** FastAPI serves both the REST/SSE backend APIs and the compiled React single-page frontend (`frontend/dist`) from a single port with zero CORS overhead.
* **Cloud & Local Vector Storage:** Supports both **Qdrant Cloud** (`QDRANT_URL` + `QDRANT_API_KEY`) and local disk fallback (`./qdrant_db`), including a zero-re-embedding migration utility (`migrate_to_cloud.py`).
* **Automated Ragas Evaluation:** Includes an LLM-as-a-Judge evaluation suite (`eval.py`) measuring **Faithfulness**, **Context Recall**, and **Answer Correctness** against a curated Golden Dataset.

---

## Architecture Overview

```text
┌───────────────────────────────────────────────────────────────────┐
│                React + TypeScript + Tailwind UI                   │
│   (Chapter Filter • Objective/Subjective Toggle • Marks Pills)    │
└─────────────────────────────────┬─────────────────────────────────┘
                                  │ HTTP / SSE (Same-Origin :8000)
                                  ▼
┌───────────────────────────────────────────────────────────────────┐
│                     FastAPI + Uvicorn Server                      │
│  • GET  /api/v1/chapters      (Lists indexed PDFs)                │
│  • POST /api/v1/query         (Dynamic Hybrid Search + Grounding) │
│  • POST /api/v1/query/stream  (Real-time SSE token streaming)     │
└─────────────────┬───────────────────────────────┬─────────────────┘
                  │                               │
                  ▼                               ▼
┌─────────────────────────────────┐ ┌───────────────────────────────┐
│      Qdrant Vector Database     │ │      Google Gemini API        │
│  • Dense: gemini-embedding-001  │ │  • LLM: gemini-3.5-flash-lite │
│  • Sparse: Qdrant/bm25          │ │  • Strict citation prompting  │
└─────────────────────────────────┘ └───────────────────────────────┘
```

---

## Project Structure

```text
textbook_rag/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI routes, lifespan lifecycle & static frontend mount
│   ├── rag_engine.py        # TextbookRAG engine, dynamic marks/type routing & SSE streaming
│   └── schemas.py           # Pydantic request & response contracts
├── frontend/
│   ├── package.json         # React 19, Vite, Tailwind CSS v4, Lucide Icons, React Markdown
│   ├── vite.config.ts       # Dev proxy & production build config
│   └── src/
│       ├── App.tsx          # Split-screen study workspace & quick study action chips
│       ├── api/ragClient.ts # Typed fetch wrapper for backend endpoints
│       └── components/      # ExamControls & SourcesDrawer components
├── textbook/                # Source NCERT chapter PDFs
├── ingest.py                # Offline PDF/OCR Markdown parser & Qdrant indexer
├── migrate_to_cloud.py      # Migrates local Qdrant vectors & payloads to Qdrant Cloud
├── eval.py                  # Ragas LLM-as-a-Judge evaluation & Markdown/CSV reporter
├── eval_dataset.json        # Golden dataset of NCERT questions & ground-truth answers
├── requirements.txt         # Python backend & RAG dependencies
└── .env.example             # Environment variable template
```

---

## Quickstart Setup

### 1. Clone & Configure Environment
```bash
git clone <your-repo-url>
cd textbook_rag
cp .env.example .env
```
Edit `.env` and add your credentials:
```env
GEMINI_API_KEY=your_gemini_api_key_here
QDRANT_URL=https://qdrant.io
QDRANT_API_KEY=your_qdrant_cloud_api_key_here
```
*(Leave `QDRANT_URL` unset if you want to run using a local `./qdrant_db` folder.)*

### 2. Install Python Backend Dependencies
```bash
python -m venv venv
# Windows PowerShell:
.\venv\Scripts\Activate.ps1
# macOS / Linux:
# source venv/bin/activate

pip install -r requirements.txt
```

### 3. Ingest Textbook PDFs (First-Time Setup)
Place your NCERT `.pdf` files inside `textbook/` and run:
```bash
python ingest.py
```

### 4. Build the React Frontend
```bash
cd frontend
npm install
npm run build
cd ..
```

### 5. Run the Unified Application
```bash
uvicorn app.main:app --reload
```
Open **`http://127.0.0.1:8000`** in your browser to use the Study Desk UI, or **`http://127.0.0`** to explore the interactive Swagger API docs.

---

## Running Automated Ragas Evaluations

To benchmark retrieval and answer faithfulness against `eval_dataset.json`:
```bash
python eval.py
```
This outputs aggregate scores in the terminal and saves both a summary CSV and a formatted Markdown report inside `eval_reports/`.

---

## API Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Health check endpoint |
| `GET` | `/api/v1/chapters` | Returns all unique indexed textbook chapter filenames |
| `POST` | `/api/v1/query` | Accepts `{ question, marks, question_type, chapter }` and returns grounded answer + source excerpts |
| `POST` | `/api/v1/query/stream` | Streams tokens in real time via Server-Sent Events (`text/event-stream`) |