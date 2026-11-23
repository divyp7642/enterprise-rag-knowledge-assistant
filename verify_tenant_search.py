
from sqlalchemy.orm import configure_mappers

from app.db.database import SessionLocal

# Register SQLAlchemy models.
from app.models.organization import Organization
from app.models.user import User
from app.models.document import Document, DocumentChunk

from app.rag.semantic_search import semantic_search


def main():
    configure_mappers()

    question = "What are the software engineering interview questions?"

    db = SessionLocal()

    try:
        for organization_id in (1, 2):
            print(f"\nTesting Organization {organization_id}")

            results = semantic_search(
                db=db,
                query=question,
                organization_id=organization_id,
                top_k=5,
            )

            print("Results returned:", len(results))

            for result in results:
                print(
                    "Document ID:",
                    result["document_id"],
                    "| Similarity:",
                    result["similarity"],
                )

                expected_document_id = organization_id

                assert result["document_id"] == expected_document_id, (
                    "SECURITY FAILURE: Cross-organization "
                    "document retrieval detected!"
                )

            print("Organization isolation check PASSED")

        print("\nAll tenant isolation checks PASSED!")

    finally:
        db.close()


if __name__ == "__main__":
    main()
