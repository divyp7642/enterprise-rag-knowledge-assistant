
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.dialects import postgresql

# Register related SQLAlchemy models before
# compiling ORM queries.
from app.models.organization import Organization
from app.models.user import User
from app.models.document import Document, DocumentChunk

from app.rag.semantic_search import semantic_search


TEST_ORGANIZATION_ID = 1


def get_compiled_query(db):
    """
    Retrieve and compile the SQL statement
    passed to the mocked database.
    """

    statement = db.execute.call_args.args[0]

    return statement.compile(
        dialect=postgresql.dialect()
    )


def test_empty_query():
    with pytest.raises(
        ValueError,
        match="Search query cannot be empty",
    ):
        semantic_search(
            db=None,
            query="",
            organization_id=TEST_ORGANIZATION_ID,
            top_k=3,
        )


def test_whitespace_query():
    with pytest.raises(
        ValueError,
        match="Search query cannot be empty",
    ):
        semantic_search(
            db=None,
            query="   ",
            organization_id=TEST_ORGANIZATION_ID,
            top_k=3,
        )


def test_invalid_top_k():
    with pytest.raises(
        ValueError,
        match="top_k must be positive",
    ):
        semantic_search(
            db=None,
            query="What is RAG?",
            organization_id=TEST_ORGANIZATION_ID,
            top_k=0,
        )


def test_invalid_organization_id():
    with pytest.raises(
        ValueError,
        match="Invalid organization ID",
    ):
        semantic_search(
            db=None,
            query="What is RAG?",
            organization_id=0,
            top_k=3,
        )


@patch("app.rag.semantic_search.EmbeddingService")
def test_successful_semantic_search(
    mock_embedding_service,
):
    mock_embedding_service.return_value.generate_embeddings.return_value = [
        [0.1] * 1536
    ]

    chunk = MagicMock()
    chunk.id = 1
    chunk.document_id = 10
    chunk.content = (
        "RAG combines retrieval and generation."
    )

    db = MagicMock()
    db.execute.return_value.all.return_value = [
        (chunk, 0.2)
    ]

    results = semantic_search(
        db=db,
        query="What is RAG?",
        organization_id=TEST_ORGANIZATION_ID,
        top_k=1,
    )

    assert results == [
        {
            "chunk_id": 1,
            "document_id": 10,
            "content": (
                "RAG combines retrieval and generation."
            ),
            "similarity": 0.8,
        }
    ]

    db.execute.assert_called_once()


@patch("app.rag.semantic_search.EmbeddingService")
def test_no_matching_documents(
    mock_embedding_service,
):
    mock_embedding_service.return_value.generate_embeddings.return_value = [
        [0.1] * 1536
    ]

    db = MagicMock()
    db.execute.return_value.all.return_value = []

    results = semantic_search(
        db=db,
        query="Unrelated question",
        organization_id=TEST_ORGANIZATION_ID,
        top_k=3,
    )

    assert results == []


@patch("app.rag.semantic_search.EmbeddingService")
def test_organization_id_is_used_in_query(
    mock_embedding_service,
):
    """
    Verify the generated SQL joins documents
    and filters by organization ID.
    """

    mock_embedding_service.return_value.generate_embeddings.return_value = [
        [0.1] * 1536
    ]

    db = MagicMock()
    db.execute.return_value.all.return_value = []

    semantic_search(
        db=db,
        query="What is RAG?",
        organization_id=2,
        top_k=3,
    )

    compiled = get_compiled_query(db)

    sql = str(compiled)

    assert "JOIN documents" in sql
    assert "documents.organization_id" in sql

    organization_values = [
        value
        for key, value in compiled.params.items()
        if "organization_id" in key
    ]

    assert 2 in organization_values


@patch("app.rag.semantic_search.EmbeddingService")
def test_different_organizations_generate_different_queries(
    mock_embedding_service,
):
    """
    Verify each organization receives its
    own SQL filter parameter.
    """

    mock_embedding_service.return_value.generate_embeddings.return_value = [
        [0.1] * 1536
    ]

    db = MagicMock()
    db.execute.return_value.all.return_value = []

    semantic_search(
        db=db,
        query="Company policy",
        organization_id=1,
        top_k=3,
    )

    compiled_org_1 = get_compiled_query(db)

    semantic_search(
        db=db,
        query="Company policy",
        organization_id=2,
        top_k=3,
    )

    compiled_org_2 = get_compiled_query(db)

    org_1_values = [
        value
        for key, value in compiled_org_1.params.items()
        if "organization_id" in key
    ]

    org_2_values = [
        value
        for key, value in compiled_org_2.params.items()
        if "organization_id" in key
    ]

    assert 1 in org_1_values
    assert 2 in org_2_values


@patch("app.rag.semantic_search.EmbeddingService")
def test_top_k_is_applied_to_query(
    mock_embedding_service,
):
    """
    Verify the SQL query applies the
    requested result limit.
    """

    mock_embedding_service.return_value.generate_embeddings.return_value = [
        [0.1] * 1536
    ]

    db = MagicMock()
    db.execute.return_value.all.return_value = []

    semantic_search(
        db=db,
        query="What is RAG?",
        organization_id=1,
        top_k=5,
    )

    compiled = get_compiled_query(db)

    assert 5 in compiled.params.values()
    assert "LIMIT" in str(compiled).upper()
