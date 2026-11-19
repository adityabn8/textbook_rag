import os
import qdrant_client
from dotenv import load_dotenv
from llama_index.core import Settings, StorageContext, VectorStoreIndex
from llama_index.core.prompts import PromptTemplate
from llama_index.core.vector_stores import MetadataFilter, MetadataFilters
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
from llama_index.llms.google_genai import GoogleGenAI
from llama_index.vector_stores.qdrant import QdrantVectorStore

load_dotenv()

QA_PROMPT = PromptTemplate(
    "You are a strict CBSE exam assistant. Answer the question ONLY using the "
    "provided textbook context. Always cite the source chapter filename. "
    "If the context does not contain the answer, state: 'The textbook does not cover this.'\n\n"
    "Context:\n---------------------\n{context_str}\n---------------------\n"
    "Question: {query_str}\nAnswer: "
)


class TextbookRAG:
    def __init__(self, qdrant_path: str = "./qdrant_db"):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY missing in .env file.")
        if not os.path.exists(qdrant_path):
            raise FileNotFoundError(f"Qdrant DB not found at '{qdrant_path}'. Run ingest.py first.")

        Settings.embed_model = GoogleGenAIEmbedding(
            model_name="gemini-embedding-001",
            api_key=api_key,
        )
        Settings.llm = GoogleGenAI(
            model="gemini-3.5-flash-lite",
            api_key=api_key,
        )

        self.client = qdrant_client.QdrantClient(path=qdrant_path)
        vector_store = QdrantVectorStore(
            client=self.client,
            collection_name="exam_prep",
            enable_hybrid=True,
            fastembed_sparse_model="Qdrant/bm25",
        )
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        self.index = VectorStoreIndex.from_vector_store(
            vector_store, storage_context=storage_context
        )




    def _resolve_exam_params(self, marks: int, question_type: str) -> dict:
        """Returns dynamic retrieval depths, alpha weight, and prompt formatting rules."""
        if question_type == "objective" or marks == 1:
            return {
                "dense_k": 3,
                "sparse_k": 6,
                "alpha": 0.35,  # Favor exact keyword/entity matching
                "format_rule": "Give a direct, concise 1-mark objective answer (1-2 sentences or exact option).",
            }
        elif marks <= 3:
            return {
                "dense_k": 4,
                "sparse_k": 6,
                "alpha": 0.50,  # Equal balance of keywords and meaning
                "format_rule": f"Write a structured {marks}-mark short answer in 3-4 clear bullet points (~40-60 words).",
            }
        else:
            return {
                "dense_k": 7,
                "sparse_k": 8,
                "alpha": 0.65,  # Favor broader conceptual themes across the chapter
                "format_rule": f"Write a comprehensive {marks}-mark long answer with a brief intro, detailed points, and conclusion (~100-120 words).",
            }

    def get_chapters(self) -> list[str]:
        """Fetches all unique ingested PDF filenames from Qdrant metadata."""
        chapters = set()
        next_offset = None

        while True:
            records, next_offset = self.client.scroll(
                collection_name="exam_prep",
                limit=100,
                offset=next_offset,
                with_payload=["file_name"],
                with_vectors=False,
            )
            for record in records:
                if record.payload and "file_name" in record.payload:
                    chapters.add(record.payload["file_name"])

            if next_offset is None:
                break

        return sorted(chapters)

    
    def ask(
        self,
        question: str,
        marks: int = 2,
        question_type: str = "subjective",
        chapter: str | None = None,
    ) -> dict:
        params = self._resolve_exam_params(marks, question_type)

        filters = None
        if chapter:
            filters = MetadataFilters(
                filters=[MetadataFilter(key="file_name", value=chapter)]
            )

        query_engine = self.index.as_query_engine(
            vector_store_query_mode="hybrid",
            similarity_top_k=params["dense_k"],
            sparse_top_k=params["sparse_k"],
            alpha=params["alpha"],
            filters=filters,
        )
        query_engine.update_prompts({"response_synthesizer:text_qa_template": QA_PROMPT})

        formatted_query = f"{question}\n\n[Exam Formatting Instruction: {params['format_rule']}]"
        response = query_engine.query(formatted_query)

        sources = [
            {
                "file_name": node.metadata.get("file_name", "Unknown"),
                "score": round(node.score or 0.0, 4),
                "text_preview": node.get_content()[:200].replace("\n", " ") + "...",
            }
            for node in response.source_nodes
        ]

        return {
            "question": question,
            "answer": str(response),
            "sources": sources,
            "full_contexts": [node.get_content() for node in response.source_nodes],
        }

    def close(self):
        self.client.close()
