import os
import qdrant_client
from dotenv import load_dotenv
from google.genai.errors import ClientError, ServerError
from llama_index.core import Settings, StorageContext, VectorStoreIndex
from llama_index.core.prompts import PromptTemplate
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
from llama_index.llms.google_genai import GoogleGenAI
from llama_index.vector_stores.qdrant import QdrantVectorStore

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found! Check your .env file.")

QDRANT_PATH = "./qdrant_db"
if not os.path.exists(QDRANT_PATH):
    raise FileNotFoundError("Qdrant database not found! Run 'python ingest.py' first.")

# 1. Configure Gemini Dense Embedding and Flash-Lite LLM
Settings.embed_model = GoogleGenAIEmbedding(
    model_name="gemini-embedding-001",
    api_key=GEMINI_API_KEY,
)

Settings.llm = GoogleGenAI(
    model="gemini-3.5-flash-lite",
    api_key=GEMINI_API_KEY,
)

# 2. Connect to Qdrant with lightweight BM25 + Gemini Dense Hybrid Search
client = qdrant_client.QdrantClient(path=QDRANT_PATH)
vector_store = QdrantVectorStore(
    client=client,
    collection_name="exam_prep",
    enable_hybrid=True,
    fastembed_sparse_model="Qdrant/bm25",
)
storage_context = StorageContext.from_defaults(vector_store=vector_store)
index = VectorStoreIndex.from_vector_store(vector_store, storage_context=storage_context)

# 3. Configure Hybrid Query Engine
query_engine = index.as_query_engine(
    vector_store_query_mode="hybrid",
    similarity_top_k=4,
    sparse_top_k=4,
    alpha=0.5,  # Balanced weight between semantic meaning and exact keywords
    streaming=True,
)

qa_prompt = PromptTemplate(
    "You are a strict CBSE exam assistant. Answer the question ONLY using the "
    "provided textbook context. Always cite the source chapter filename. "
    "If the context does not contain the answer, state: 'The textbook does not cover this.'\n\n"
    "Context:\n---------------------\n{context_str}\n---------------------\n"
    "Question: {query_str}\nAnswer: "
)
query_engine.update_prompts({"response_synthesizer:text_qa_template": qa_prompt})

# 4. Interactive Exam Q&A Loop
print("Ready (Qdrant Hybrid Search)! Ask an exam question (or type 'exit' to quit):")
while True:
    question = input("\nQuestion: ").strip()
    if question.lower() in {"exit", "quit"}:
        break
    if not question:
        continue

    try:
        print("\nAnswer: ", end="", flush=True)
        streaming_response = query_engine.query(question)
        streaming_response.print_response_stream()

        print("\n\nSources used:")
        for node in streaming_response.source_nodes:
            print("-", node.metadata.get("file_name"), "| Hybrid Score:", round(node.score, 4))

    except (ServerError, ClientError) as e:
        print(f"\n[Gemini API Notice]: {e.message}")
        print("Wait a few seconds and try your question again.")