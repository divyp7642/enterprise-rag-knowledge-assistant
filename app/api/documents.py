
from io import BytesIO

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
)
from pypdf import PdfReader
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.services.cache_service import CacheService
from app.services.document_service import save_document


router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)

MAX_FILE_SIZE = 10 * 1024 * 1024


@router.post("/upload", status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        if (
            not file.filename
            or not file.filename.lower().endswith(".pdf")
        ):
            raise HTTPException(
                status_code=400,
                detail="Only PDF files are allowed",
            )

        if file.content_type != "application/pdf":
            raise HTTPException(
                status_code=400,
                detail="Invalid PDF content type",
            )

        content = await file.read(MAX_FILE_SIZE + 1)

        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail="PDF exceeds the 10 MB limit",
            )

        if not content.startswith(b"%PDF-"):
            raise HTTPException(
                status_code=400,
                detail="Invalid PDF file",
            )

        try:
            reader = PdfReader(BytesIO(content))

            if reader.is_encrypted:
                raise HTTPException(
                    status_code=400,
                    detail="Encrypted PDFs are not supported",
                )

            extracted_text = "\n".join(
                page.extract_text() or ""
                for page in reader.pages
            )

        except HTTPException:
            raise

        except Exception:
            raise HTTPException(
                status_code=400,
                detail="Unable to process PDF",
            )

        if not extracted_text.strip():
            raise HTTPException(
                status_code=400,
                detail="No extractable text found in PDF",
            )

        document, chunk_count = save_document(
            db=db,
            filename=file.filename,
            content_type=file.content_type,
            extracted_text=extracted_text,
            organization_id=current_user.organization_id,
            uploaded_by_user_id=current_user.id,
        )

        # Invalidate only this organization's RAG cache.
        cache_service = CacheService()

        cache_invalidated = (
            cache_service.invalidate_rag_cache(
                organization_id=current_user.organization_id
            )
        )

        return {
            "document_id": document.id,
            "filename": document.filename,
            "pages": len(reader.pages),
            "characters_extracted": len(extracted_text),
            "chunks_created": chunk_count,
            "cache_invalidated": cache_invalidated,
            "message": "Document saved successfully",
        }

    except HTTPException:
        raise

    except SQLAlchemyError:
        raise HTTPException(
            status_code=500,
            detail="Database error while saving document",
        )

    finally:
        await file.close()
