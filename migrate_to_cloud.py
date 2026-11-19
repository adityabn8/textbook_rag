import os
import qdrant_client
from dotenv import load_dotenv
from qdrant_client.models import (
    Distance,
    Modifier,
    PointStruct,
    SparseVectorParams,
    VectorParams,
)

load_dotenv()

LOCAL_PATH = "./qdrant_db"
COLLECTION_NAME = "exam_prep"
CLOUD_URL = os.getenv("QDRANT_URL")
CLOUD_API_KEY = os.getenv("QDRANT_API_KEY")

if not CLOUD_URL or not CLOUD_API_KEY:
    raise ValueError("Please set QDRANT_URL and QDRANT_API_KEY in your .env file first!")

print("Opening local Qdrant DB and connecting to Qdrant Cloud...")
local_client = qdrant_client.QdrantClient(path=LOCAL_PATH)
cloud_client = qdrant_client.QdrantClient(
    url=CLOUD_URL,
    api_key=CLOUD_API_KEY,
    prefer_grpc=True,
)

try:
    # 1. Inspect local collection schema (vector sizes & sparse BM25 config)
    local_info = local_client.get_collection(COLLECTION_NAME)
    dense_cfg = local_info.config.params.vectors
    sparse_cfg = local_info.config.params.sparse_vectors

    # Handle named dense vectors (LlamaIndex default: 'text-dense' & 'text-sparse')
    if isinstance(dense_cfg, dict):
        vectors_config = {
            name: VectorParams(size=cfg.size, distance=cfg.distance)
            for name, cfg in dense_cfg.items()
        }
    else:
        vectors_config = VectorParams(size=dense_cfg.size, distance=dense_cfg.distance)

    sparse_vectors_config = None
    if sparse_cfg:
        sparse_vectors_config = {
            name: SparseVectorParams(modifier=cfg.modifier or Modifier.NONE)
            for name, cfg in sparse_cfg.items()
        }

    # 2. Create matching collection on Qdrant Cloud
    if cloud_client.collection_exists(COLLECTION_NAME):
        print(f"Collection '{COLLECTION_NAME}' already exists on Cloud—recreating cleanly...")
        cloud_client.delete_collection(COLLECTION_NAME)

    cloud_client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=vectors_config,
        sparse_vectors_config=sparse_vectors_config,
    )
    print(f"Created collection '{COLLECTION_NAME}' on Qdrant Cloud.")

    # 3. Scroll all points (dense + sparse vectors + payloads) and batch-upsert to Cloud
    total_migrated = 0
    next_offset = None

    while True:
        records, next_offset = local_client.scroll(
            collection_name=COLLECTION_NAME,
            limit=50,
            offset=next_offset,
            with_payload=True,
            with_vectors=True,
        )
        if not records:
            break

        points = [
            PointStruct(
                id=rec.id,
                vector=rec.vector,
                payload=rec.payload,
            )
            for rec in records
        ]

        cloud_client.upsert(collection_name=COLLECTION_NAME, points=points, wait=True)
        total_migrated += len(points)
        print(f"Migrated {total_migrated} chunks to Qdrant Cloud...")

        if next_offset is None:
            break

    print(f"\nMigration complete! Total chunks in Qdrant Cloud: {cloud_client.count(COLLECTION_NAME).count}")

finally:
    local_client.close()
    cloud_client.close()