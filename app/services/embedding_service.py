
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentChunk
from app.rag.embeddings import EmbeddingService
from app.services.cache_service import CacheService


def embed_document_chunks(
    db: Session,
    document_id: int,
    organization_id: int,
) -> int:
    """
    Generate embeddings for pending chunks
    belonging to a document in the
    authenticated user's organization.
    """

    if document_id <= 0:
        raise ValueError("Invalid document ID")

    if organization_id <= 0:
        raise ValueError("Invalid organization ID")

    document = db.scalar(
        select(Document).where(
            Document.id == document_id,
            Document.organization_id == organization_id,
        )
    )

    if document is None:
        raise ValueError(
            "Document not found in this organization"
        )

    chunks = db.scalars(
        select(DocumentChunk)
        .where(
            DocumentChunk.document_id == document.id,
            DocumentChunk.embedding.is_(None),
        )
        .order_by(DocumentChunk.chunk_index)
    ).all()

    if not chunks:
        return 0

    service = EmbeddingService()

    embeddings = service.generate_embeddings(
        [chunk.content for chunk in chunks]
    )

    try:
        for chunk, embedding in zip(
            chunks,
            embeddings,
            strict=True,
        ):
            chunk.embedding = embedding

        db.commit()

    except Exception:
        db.rollback()
        raise

    # Invalidate only the document owner's
    # cached answers after a successful commit.
    cache_service = CacheService()

    cache_service.invalidate_rag_cache(
        organization_id=organization_id
    )

    return len(chunks)
