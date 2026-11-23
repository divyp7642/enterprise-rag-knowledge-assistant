
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentChunk


def split_text(
    text: str,
    chunk_size: int = 1000,
    overlap: int = 200,
) -> list[str]:
    if chunk_size <= 0 or not 0 <= overlap < chunk_size:
        raise ValueError("Invalid chunk configuration")

    chunks = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end == len(text):
            break

        start = end - overlap

    return chunks


def save_document(
    db: Session,
    filename: str,
    content_type: str,
    extracted_text: str,
    organization_id: int,
    uploaded_by_user_id: int,
) -> tuple[Document, int]:
    """
    Save a document and its chunks under
    the authenticated user's organization.
    """

    if organization_id <= 0 or uploaded_by_user_id <= 0:
        raise ValueError("Invalid document ownership")

    chunks = split_text(extracted_text)

    if not chunks:
        raise ValueError("Document contains no text")

    try:
        document = Document(
            filename=filename,
            content_type=content_type,
            organization_id=organization_id,
            uploaded_by=uploaded_by_user_id,
        )

        db.add(document)
        db.flush()

        for index, content in enumerate(chunks):
            db.add(
                DocumentChunk(
                    document_id=document.id,
                    chunk_index=index,
                    content=content,
                    embedding=None,
                )
            )

        db.commit()
        db.refresh(document)

        return document, len(chunks)

    except Exception:
        db.rollback()
        raise
