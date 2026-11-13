"""Persistent Vector Store implementation using Qdrant local."""
import uuid
from pathlib import Path
from typing import Any
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from .models import Chunk


class QdrantVectorStore:
    """Production vector store using local persistent Qdrant."""

    def __init__(self, storage_path: str = "./qdrant_db", dimensions: int = 3072) -> None:
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.dimensions = dimensions
        self.client = QdrantClient(path=str(self.storage_path))
        print(f"[VectorStore] Initialized local Qdrant at: {self.storage_path.resolve()}")

    def create_schema(self, strategy: str) -> None:
        """Ensure collection exists for the given strategy with Cosine metric."""
        collections = [c.name for c in self.client.get_collections().collections]
        if strategy not in collections:
            self.client.create_collection(
                collection_name=strategy,
                vectors_config=qmodels.VectorParams(
                    size=self.dimensions,
                    distance=qmodels.Distance.COSINE
                )
            )
            print(f"[VectorStore] Created collection: {strategy} (dim: {self.dimensions}, metric: Cosine)")
        else:
            print(f"[VectorStore] Collection already exists: {strategy}")

    def upsert(self, strategy: str, chunks: list[Chunk], vectors: list[list[float]], batch_size: int = 100) -> None:
        """Store chunks and vectors with stable IDs and payload."""
        if len(chunks) != len(vectors):
            raise ValueError(f"Chunks count ({len(chunks)}) != vectors count ({len(vectors)})")

        self.create_schema(strategy)

        points = []
        for chunk, vector in zip(chunks, vectors):
            # Generate deterministic UUID based on chunk_id so repeated ingestion does not duplicate
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk.chunk_id))
            payload = {
                "chunk_id": chunk.chunk_id,
                "document_id": chunk.document_id,
                "source": chunk.source,
                "page": chunk.page,
                "text": chunk.text,
                "metadata": chunk.metadata,
                "section": chunk.metadata.get("section", "")
            }
            points.append(
                qmodels.PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload
                )
            )

        for i in range(0, len(points), batch_size):
            batch = points[i : i + batch_size]
            self.client.upsert(
                collection_name=strategy,
                points=batch
            )

        print(f"[VectorStore] Upserted {len(points)} vectors into collection '{strategy}'")

    def search(
        self,
        strategy: str,
        query_vector: list[float],
        top_k: int = 3,
        filters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Search top-k chunks by cosine distance, optionally applying metadata filters."""
        query_filter = None
        if filters:
            conditions = []
            for k, v in filters.items():
                # Support filtering on top-level payload or nested metadata
                conditions.append(
                    qmodels.FieldCondition(
                        key=f"metadata.{k}",
                        match=qmodels.MatchValue(value=v)
                    )
                )
            if conditions:
                query_filter = qmodels.Filter(must=conditions)

        search_result = self.client.query_points(
            collection_name=strategy,
            query=query_vector,
            limit=top_k,
            query_filter=query_filter
        )

        hits: list[dict[str, Any]] = []
        for pt in search_result.points:
            payload = pt.payload or {}
            hits.append({
                "chunk_id": payload.get("chunk_id", str(pt.id)),
                "document_id": payload.get("document_id", ""),
                "source": payload.get("source", ""),
                "page": payload.get("page", 0),
                "text": payload.get("text", ""),
                "metadata": payload.get("metadata", {}),
                "score": float(pt.score) if pt.score is not None else 0.0
            })

        return hits
