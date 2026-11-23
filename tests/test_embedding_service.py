
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.services.embedding_service import embed_document_chunks


TEST_DOCUMENT_ID = 2
TEST_ORGANIZATION_ID = 2


def create_mock_db(
    chunks=None,
    document_exists=True,
):
    """
    Create a fake database session that
    simulates document ownership and chunks.
    """
    db = MagicMock()

    if document_exists:
        db.scalar.return_value = SimpleNamespace(
            id=TEST_DOCUMENT_ID,
            organization_id=TEST_ORGANIZATION_ID,
        )
    else:
        db.scalar.return_value = None

    db.scalars.return_value.all.return_value = (
        chunks if chunks is not None else []
    )

    return db


@patch("app.services.embedding_service.CacheService")
@patch("app.services.embedding_service.EmbeddingService")
def test_embedding_success(
    mock_embedding_class,
    mock_cache_class,
):
    chunk = MagicMock()
    chunk.content = "Enterprise RAG document"

    db = create_mock_db(chunks=[chunk])

    mock_embedding_class.return_value.generate_embeddings.return_value = [
        [0.1, 0.2, 0.3]
    ]

    result = embed_document_chunks(
        db=db,
        document_id=TEST_DOCUMENT_ID,
        organization_id=TEST_ORGANIZATION_ID,
    )

    assert result == 1
    assert chunk.embedding == [0.1, 0.2, 0.3]

    db.commit.assert_called_once()

    mock_cache_class.return_value.invalidate_rag_cache.assert_called_once_with(
        organization_id=TEST_ORGANIZATION_ID
    )


@patch("app.services.embedding_service.CacheService")
@patch("app.services.embedding_service.EmbeddingService")
def test_embedding_database_failure(
    mock_embedding_class,
    mock_cache_class,
):
    chunk = MagicMock()
    chunk.content = "Test document"

    db = create_mock_db(chunks=[chunk])

    db.commit.side_effect = RuntimeError(
        "Database failure"
    )

    mock_embedding_class.return_value.generate_embeddings.return_value = [
        [0.1, 0.2, 0.3]
    ]

    with pytest.raises(
        RuntimeError,
        match="Database failure",
    ):
        embed_document_chunks(
            db=db,
            document_id=TEST_DOCUMENT_ID,
            organization_id=TEST_ORGANIZATION_ID,
        )

    db.rollback.assert_called_once()
    mock_cache_class.assert_not_called()


@patch("app.services.embedding_service.CacheService")
@patch("app.services.embedding_service.EmbeddingService")
def test_no_pending_embeddings(
    mock_embedding_class,
    mock_cache_class,
):
    db = create_mock_db(chunks=[])

    result = embed_document_chunks(
        db=db,
        document_id=TEST_DOCUMENT_ID,
        organization_id=TEST_ORGANIZATION_ID,
    )

    assert result == 0

    db.commit.assert_not_called()
    mock_embedding_class.assert_not_called()
    mock_cache_class.assert_not_called()


def test_invalid_document_id():
    db = MagicMock()

    with pytest.raises(
        ValueError,
        match="Invalid document ID",
    ):
        embed_document_chunks(
            db=db,
            document_id=0,
            organization_id=TEST_ORGANIZATION_ID,
        )

    db.scalar.assert_not_called()
    db.commit.assert_not_called()


def test_invalid_organization_id():
    db = MagicMock()

    with pytest.raises(
        ValueError,
        match="Invalid organization ID",
    ):
        embed_document_chunks(
            db=db,
            document_id=TEST_DOCUMENT_ID,
            organization_id=0,
        )

    db.scalar.assert_not_called()
    db.commit.assert_not_called()


@patch("app.services.embedding_service.EmbeddingService")
def test_document_not_in_organization(
    mock_embedding_class,
):
    db = create_mock_db(
        document_exists=False
    )

    with pytest.raises(
        ValueError,
        match="Document not found in this organization",
    ):
        embed_document_chunks(
            db=db,
            document_id=TEST_DOCUMENT_ID,
            organization_id=1,
        )

    db.scalars.assert_not_called()
    db.commit.assert_not_called()
    mock_embedding_class.assert_not_called()


@patch("app.services.embedding_service.CacheService")
@patch("app.services.embedding_service.EmbeddingService")
def test_multiple_chunks_embedded(
    mock_embedding_class,
    mock_cache_class,
):
    chunk_1 = MagicMock()
    chunk_1.content = "First document chunk"

    chunk_2 = MagicMock()
    chunk_2.content = "Second document chunk"

    db = create_mock_db(
        chunks=[chunk_1, chunk_2]
    )

    mock_embedding_class.return_value.generate_embeddings.return_value = [
        [0.1, 0.2, 0.3],
        [0.4, 0.5, 0.6],
    ]

    result = embed_document_chunks(
        db=db,
        document_id=TEST_DOCUMENT_ID,
        organization_id=TEST_ORGANIZATION_ID,
    )

    assert result == 2

    assert chunk_1.embedding == [0.1, 0.2, 0.3]
    assert chunk_2.embedding == [0.4, 0.5, 0.6]

    mock_embedding_class.return_value.generate_embeddings.assert_called_once_with(
        [
            "First document chunk",
            "Second document chunk",
        ]
    )

    db.commit.assert_called_once()

    mock_cache_class.return_value.invalidate_rag_cache.assert_called_once_with(
        organization_id=TEST_ORGANIZATION_ID
    )
