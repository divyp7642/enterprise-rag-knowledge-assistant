
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from pypdf import PdfWriter

from app.core.dependencies import get_current_user
from app.db.database import get_db
from app.main import app


TEST_ORGANIZATION_ID = 2
TEST_USER_ID = 2


def create_test_pdf():
    writer = PdfWriter()

    writer.add_blank_page(
        width=612,
        height=792,
    )

    writer.add_metadata({
        "/Title": "Test Document",
    })

    buffer = BytesIO()
    writer.write(buffer)

    return buffer.getvalue()


def fake_pdf_reader():
    reader = MagicMock()
    reader.is_encrypted = False

    page = MagicMock()
    page.extract_text.return_value = (
        "This is a sample enterprise document."
    )

    reader.pages = [page]

    return reader


def fake_authenticated_user():
    return SimpleNamespace(
        id=TEST_USER_ID,
        organization_id=TEST_ORGANIZATION_ID,
    )


def upload_test_pdf(client):
    return client.post(
        "/documents/upload",
        files={
            "file": (
                "test.pdf",
                create_test_pdf(),
                "application/pdf",
            )
        },
    )


def test_upload_requires_authentication():
    """
    Uploading without a JWT must return 401.
    """

    app.dependency_overrides.clear()

    try:
        with TestClient(app) as client:
            response = upload_test_pdf(client)

        assert response.status_code == 401
        assert response.json()["detail"] == (
            "Invalid or missing authentication token"
        )

    finally:
        app.dependency_overrides.clear()


def test_authenticated_upload_succeeds():
    """
    Authenticated users can upload PDFs.
    """

    fake_db = MagicMock()

    app.dependency_overrides[get_db] = lambda: fake_db
    app.dependency_overrides[get_current_user] = (
        fake_authenticated_user
    )

    try:
        with (
            patch(
                "app.api.documents.PdfReader",
                return_value=fake_pdf_reader(),
            ),
            patch(
                "app.api.documents.save_document",
                return_value=(
                    SimpleNamespace(
                        id=1,
                        filename="test.pdf",
                    ),
                    1,
                ),
            ) as mock_save,
            patch(
                "app.api.documents.CacheService",
            ) as mock_cache_class,
        ):
            mock_cache = mock_cache_class.return_value
            mock_cache.invalidate_rag_cache.return_value = True

            with TestClient(app) as client:
                response = upload_test_pdf(client)

            assert response.status_code == 201

            data = response.json()

            assert data["document_id"] == 1
            assert data["filename"] == "test.pdf"
            assert data["pages"] == 1
            assert data["chunks_created"] == 1
            assert data["cache_invalidated"] is True
            assert data["message"] == (
                "Document saved successfully"
            )

            mock_save.assert_called_once()

    finally:
        app.dependency_overrides.clear()


def test_upload_uses_authenticated_user_ownership():
    """
    The organization and uploader must come
    from the authenticated user.
    """

    fake_db = MagicMock()

    app.dependency_overrides[get_db] = lambda: fake_db
    app.dependency_overrides[get_current_user] = (
        fake_authenticated_user
    )

    try:
        with (
            patch(
                "app.api.documents.PdfReader",
                return_value=fake_pdf_reader(),
            ),
            patch(
                "app.api.documents.save_document",
                return_value=(
                    SimpleNamespace(
                        id=2,
                        filename="test.pdf",
                    ),
                    1,
                ),
            ) as mock_save,
            patch(
                "app.api.documents.CacheService",
            ) as mock_cache_class,
        ):
            mock_cache_class.return_value.invalidate_rag_cache.return_value = True

            with TestClient(app) as client:
                response = upload_test_pdf(client)

            assert response.status_code == 201

            mock_save.assert_called_once_with(
                db=fake_db,
                filename="test.pdf",
                content_type="application/pdf",
                extracted_text=(
                    "This is a sample enterprise document."
                ),
                organization_id=TEST_ORGANIZATION_ID,
                uploaded_by_user_id=TEST_USER_ID,
            )

    finally:
        app.dependency_overrides.clear()


def test_upload_invalidates_only_organization_cache():
    """
    Uploading to Organization 2 must invalidate
    only Organization 2's RAG cache.
    """

    fake_db = MagicMock()

    app.dependency_overrides[get_db] = lambda: fake_db
    app.dependency_overrides[get_current_user] = (
        fake_authenticated_user
    )

    try:
        with (
            patch(
                "app.api.documents.PdfReader",
                return_value=fake_pdf_reader(),
            ),
            patch(
                "app.api.documents.save_document",
                return_value=(
                    SimpleNamespace(
                        id=3,
                        filename="test.pdf",
                    ),
                    1,
                ),
            ),
            patch(
                "app.api.documents.CacheService",
            ) as mock_cache_class,
        ):
            mock_cache = mock_cache_class.return_value
            mock_cache.invalidate_rag_cache.return_value = True

            with TestClient(app) as client:
                response = upload_test_pdf(client)

            assert response.status_code == 201

            assert response.json()["cache_invalidated"] is True

            mock_cache.invalidate_rag_cache.assert_called_once_with(
                organization_id=TEST_ORGANIZATION_ID
            )

    finally:
        app.dependency_overrides.clear()


def test_upload_cache_failure():
    """
    A Redis invalidation failure must not
    cause a successful upload to fail.
    """

    fake_db = MagicMock()

    app.dependency_overrides[get_db] = lambda: fake_db
    app.dependency_overrides[get_current_user] = (
        fake_authenticated_user
    )

    try:
        with (
            patch(
                "app.api.documents.PdfReader",
                return_value=fake_pdf_reader(),
            ),
            patch(
                "app.api.documents.save_document",
                return_value=(
                    SimpleNamespace(
                        id=4,
                        filename="test.pdf",
                    ),
                    1,
                ),
            ),
            patch(
                "app.api.documents.CacheService",
            ) as mock_cache_class,
        ):
            mock_cache = mock_cache_class.return_value
            mock_cache.invalidate_rag_cache.return_value = False

            with TestClient(app) as client:
                response = upload_test_pdf(client)

            assert response.status_code == 201

            data = response.json()

            assert data["cache_invalidated"] is False
            assert data["message"] == (
                "Document saved successfully"
            )

            mock_cache.invalidate_rag_cache.assert_called_once_with(
                organization_id=TEST_ORGANIZATION_ID
            )

    finally:
        app.dependency_overrides.clear()
