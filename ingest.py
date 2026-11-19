import json
import logging
import os
import shutil
import time
import pymupdf4llm
import qdrant_client
from dotenv import load_dotenv
from google.genai.errors import ClientError
from llama_index.core import Document, Settings, StorageContext, VectorStoreIndex
from llama_index.core.node_parser import MarkdownNodeParser
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("TextbookIngest")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TEXTBOOK_DIR = "./textbook"
CACHE_FILE = "./parsed_chapters.json"
QDRANT_PATH = "./qdrant_db"

Settings.embed_model = GoogleGenAIEmbedding(
    model_name="gemini-embedding-001",
    api_key=GEMINI_API_KEY,
    embed_batch_size=10,
)


def load_or_extract_documents():
    if os.path.exists(CACHE_FILE):
        logger.info("Loading extracted text from '%s'...", CACHE_FILE)
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            raw_docs = json.load(f)
        return [
            Document(text=d["text"], metadata={"file_name": d["file_name"]})
            for d in raw_docs
        ]

    pdf_files = sorted(
        f for f in os.listdir(TEXTBOOK_DIR) if f.lower().endswith(".pdf")
    )
    if not pdf_files:
        raise FileNotFoundError(f"No PDF files found inside '{TEXTBOOK_DIR}'.")

    logger.info("Found %d PDF file(s) in '%s'.", len(pdf_files), TEXTBOOK_DIR)
    documents = []
    cache_data = []

    for idx, filename in enumerate(pdf_files, start=1):
        filepath = os.path.join(TEXTBOOK_DIR, filename)
        logger.info("[%d/%d] Extracting text from '%s'...", idx, len(pdf_files), filename)
        t0 = time.time()

        md_text = pymupdf4llm.to_markdown(filepath)
        documents.append(Document(text=md_text, metadata={"file_name": filename}))
        cache_data.append({"file_name": filename, "text": md_text})

        logger.info(
            "[%d/%d] Extracted %s characters in %.2fs.",
            idx,
            len(pdf_files),
            f"{len(md_text):,}",
            time.time() - t0,
        )

    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache_data, f, ensure_ascii=False)
    logger.info("Saved extracted text cache to '%s'.", CACHE_FILE)
    return documents


def ingest_textbooks(force_rebuild=True):
    start_time = time.time()

    if force_rebuild and os.path.exists(QDRANT_PATH):
        logger.info("Removing existing Qdrant database at '%s'...", QDRANT_PATH)
        shutil.rmtree(QDRANT_PATH)

    logger.info("Initializing Qdrant at '%s' with Hybrid Search...", QDRANT_PATH)
    client = qdrant_client.QdrantClient(path=QDRANT_PATH)
    vector_store = QdrantVectorStore(
        client=client,
        fastembed_sparse_model="Qdrant/bm25",
        collection_name="exam_prep",
        enable_hybrid=True,
    )
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    documents = load_or_extract_documents()

    logger.info("Splitting %d document(s) into Markdown chunks...", len(documents))
    nodes = MarkdownNodeParser().get_nodes_from_documents(documents)
    total_nodes = len(nodes)
    logger.info("Created %d structured chunks.", total_nodes)

    index = VectorStoreIndex([], storage_context=storage_context)
    batch_size = 20

    for i in range(0, total_nodes, batch_size):
        batch = nodes[i : i + batch_size]
        end_idx = min(i + batch_size, total_nodes)

        while True:
            try:
                logger.info("Embedding and indexing chunks %d to %d of %d...", i + 1, end_idx, total_nodes)
                index.insert_nodes(batch)
                break
            except ClientError as e:
                if "429" in str(e):
                    logger.warning("Hit Gemini free rate limit (429). Sleeping 30s...")
                    time.sleep(30)
                else:
                    raise

        if end_idx < total_nodes:
            logger.info("Pausing 15s to respect free-tier rate limits...")
            time.sleep(15)

    logger.info(
        "SUCCESS! Ingested %d chunks into Qdrant in %.2fs.",
        total_nodes,
        time.time() - start_time,
    )


if __name__ == "__main__":
    ingest_textbooks(force_rebuild=True)