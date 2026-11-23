
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentChunk
from app.rag.embeddings import EmbeddingService


MIN_SIMILARITY = 0.30


def semantic_search(
    db: Session,
    query: str,
    organization_id: int,
    top_k: int = 3,
):
    """
    Search only document chunks belonging
    to the specified organization.
    """

    if not query.strip():
        raise ValueError("Search query cannot be empty")

    if organization_id <= 0:
        raise ValueError("Invalid organization ID")

    if top_k < 1:
        raise ValueError("top_k must be positive")

    embedding_service = EmbeddingService()

    query_embedding = (
        embedding_service.generate_embeddings([query])[0]
    )

    distance = DocumentChunk.embedding.cosine_distance(
        query_embedding
    )

    statement = (
        select(
            DocumentChunk,
            distance.label("distance"),
        )
        .join(
            Document,
            DocumentChunk.document_id == Document.id,
        )
        .where(
            Document.organization_id == organization_id
        )
        .where(
            DocumentChunk.embedding.is_not(None)
        )
        .where(
            distance <= 1 - MIN_SIMILARITY
        )
        .order_by(distance)
        .limit(top_k)
    )

    results = db.execute(statement).all()

    return [
        {
            "chunk_id": chunk.id,
            "document_id": chunk.document_id,
            "content": chunk.content,
            "similarity": round(
                1 - float(dist),
                4,
            ),
        }
        for chunk, dist in results
    ]
