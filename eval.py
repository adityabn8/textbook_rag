import asyncio
import json
import math
import os
from datetime import datetime

import pandas as pd
from dotenv import load_dotenv
from google import genai
from ragas.embeddings import GoogleEmbeddings
from ragas.llms import llm_factory
from ragas.metrics.collections import (
    AnswerCorrectness,
    ContextRecall,
    Faithfulness,
)

from app.rag_engine import TextbookRAG

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY missing in .env file!")

JUDGE_MODEL = "gemini-3.5-flash-lite"
EMBED_MODEL = "gemini-embedding-001"
MAX_CONCURRENCY = 3  # keep low to avoid Gemini 429s
MAX_RETRIES = 3


def collect_records(test_cases: list[dict]) -> list[dict]:
    """Run every question through the RAG pipeline (sync)."""
    print(f"Initializing TextbookRAG and running {len(test_cases)} test cases...")
    rag = TextbookRAG(qdrant_path="./qdrant_db")
    records = []
    try:
        for idx, item in enumerate(test_cases, start=1):
            q = item["question"]
            print(f"[{idx}/{len(test_cases)}] Querying: {q}")
            result = rag.ask(
                question=q,
                marks=item.get("marks", 3),
                question_type=item.get("question_type", "subjective"),
                chapter=item.get("chapter"),
            )
            records.append(
                {
                    "user_input": q,
                    "response": result["answer"],
                    "retrieved_contexts": result["full_contexts"],
                    "reference": item["ground_truth"],
                }
            )
    finally:
        rag.close()
    return records


async def _safe_score(name: str, coro_fn, **kwargs) -> float:
    """Call metric.ascore with retries; return NaN on failure instead of crashing the run."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            res = await coro_fn(**kwargs)
            return round(float(res.value), 4)
        except Exception as e:  # noqa: BLE001
            if attempt == MAX_RETRIES:
                print(f"   ! {name} failed after {MAX_RETRIES} tries: {type(e).__name__}: {e}")
                return math.nan
            await asyncio.sleep(2**attempt)  # 2s, 4s backoff
    return math.nan


async def grade_all(records: list[dict]) -> list[dict]:
    # Instructor requires a SYNC google.genai.Client (AsyncClient is rejected).
    # Ragas runs sync LLM clients in a worker thread when ascore() awaits them.
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    judge_llm = llm_factory(JUDGE_MODEL, provider="google", client=gemini_client)
    judge_embeddings = GoogleEmbeddings(model=EMBED_MODEL, client=gemini_client)

    faithfulness = Faithfulness(llm=judge_llm)
    recall = ContextRecall(llm=judge_llm)
    correctness = AnswerCorrectness(llm=judge_llm, embeddings=judge_embeddings)

    sem = asyncio.Semaphore(MAX_CONCURRENCY)
    total = len(records)

    async def grade_one(idx: int, rec: dict) -> dict:
        async with sem:
            print(f"Grading [{idx}/{total}]: {rec['user_input'][:55]}...")
            ctx = rec["retrieved_contexts"]
            f, r, c = await asyncio.gather(
                _safe_score(
                    "faithfulness",
                    faithfulness.ascore,
                    user_input=rec["user_input"],
                    response=rec["response"],
                    retrieved_contexts=ctx,
                ),
                _safe_score(
                    "context_recall",
                    recall.ascore,
                    user_input=rec["user_input"],
                    retrieved_contexts=ctx,
                    reference=rec["reference"],
                ),
                _safe_score(
                    "answer_correctness",
                    correctness.ascore,
                    user_input=rec["user_input"],
                    response=rec["response"],
                    reference=rec["reference"],
                ),
            )
            return {
                "question": rec["user_input"],
                "faithfulness": f,
                "context_recall": r,
                "answer_correctness": c,
                "generated_answer": rec["response"],
                "ground_truth": rec["reference"],
            }

    return await asyncio.gather(*(grade_one(i, r) for i, r in enumerate(records, 1)))


def write_reports(df: pd.DataFrame) -> None:
    os.makedirs("eval_reports", exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    csv_path = os.path.join("eval_reports", f"ragas_summary_{ts}.csv")
    df.to_csv(csv_path, index=False, encoding="utf-8")

    agg = df.mean(numeric_only=True).round(4)  # NaN rows are skipped by mean()
    try:
        agg_md = agg.to_markdown()  # needs `pip install tabulate`
    except ImportError:
        agg_md = "\n".join(f"- {k}: {v}" for k, v in agg.items())

    md_path = os.path.join("eval_reports", f"ragas_report_{ts}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Textbook RAG Evaluation Report\n\n## Aggregate Scores\n\n")
        f.write(agg_md + "\n\n## Per-Question Breakdown\n\n")
        for idx, row in df.iterrows():
            f.write(f"### Q{idx + 1}: {row['question']}\n")
            f.write(f"- **Faithfulness:** `{row['faithfulness']}`\n")
            f.write(f"- **Context Recall:** `{row['context_recall']}`\n")
            f.write(f"- **Answer Correctness:** `{row['answer_correctness']}`\n")
            f.write(f"- **Generated Answer:** {row['generated_answer']}\n")
            f.write(f"- **Expected Ground Truth:** {row['ground_truth']}\n\n---\n\n")

    print(f"\nClean CSV saved to: {csv_path}")
    print(f"Readable Markdown report saved to: {md_path}")


def run_evaluation(dataset_path: str = "eval_dataset.json"):
    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"'{dataset_path}' not found! Create it first.")
    with open(dataset_path, "r", encoding="utf-8") as f:
        test_cases = json.load(f)

    records = collect_records(test_cases)

    print("\nRunning Ragas LLM-as-a-Judge evaluation...")
    scored_rows = asyncio.run(grade_all(records))  # ONE event loop for all metrics

    df = pd.DataFrame(scored_rows)
    print("\n=== AGGREGATE RAGAS SCORES ===")
    print(df.mean(numeric_only=True).round(4))
    failed = df[["faithfulness", "context_recall", "answer_correctness"]].isna().sum().sum()
    if failed:
        print(f"WARNING: {failed} metric score(s) failed (NaN) and were excluded from means.")

    write_reports(df)


if __name__ == "__main__":
    run_evaluation()