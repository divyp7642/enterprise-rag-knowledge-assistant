
from app.db.database import SessionLocal

# Register all models before executing ORM queries.
from app.models.organization import Organization
from app.models.user import User
from app.models.document import Document, DocumentChunk

from app.services.embedding_service import embed_document_chunks


def main():
    # Document belonging to Organization 2
    document_id = 2
    organization_id = 2

    db = SessionLocal()

    try:
        count = embed_document_chunks(
            db=db,
            document_id=document_id,
            organization_id=organization_id,
        )

        print("Document ID:", document_id)
        print("Organization ID:", organization_id)
        print("Embeddings generated:", count)

        if count == 0:
            print("No pending embeddings found.")
        else:
            print("Embeddings saved successfully!")

    except Exception as exc:
        print("Embedding generation failed:", exc)
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()
