
from unittest.mock import MagicMock, patch

import pytest

from app.rag.answer_generator import RAGAnswerService


TEST_ORGANIZATION_ID = 2


@pytest.fixture
def rag_service():
    with patch.dict(
        "os.environ",
        {"OPENAI_API_KEY": "test-api-key"},
    ):
        service = RAGAnswerService()

    service.cache = MagicMock()
    service.cache.get.return_value = None
    service.cache.set.return_value = True

    return service


def test_empty_question(rag_service):
    with pytest.raises(
        ValueError,
        match="Question cannot be empty",
    ):
        rag_service.generate_answer(
            db=MagicMock(),
            question="",
            organization_id=TEST_ORGANIZATION_ID,
            top_k=3,
        )


@patch("app.rag.answer_generator.semantic_search")
def test_no_relevant_documents(
    mock_search,
    rag_service,
):
    mock_search.return_value = []

    fake_db = MagicMock()

    with patch.object(
        rag_service.client.chat.completions,
        "create",
    ) as mock_create:

        result = rag_service.generate_answer(
            db=fake_db,
            question="What is the capital of Australia?",
            organization_id=TEST_ORGANIZATION_ID,
            top_k=3,
        )

        assert result == {
            "question": "What is the capital of Australia?",
            "answer": "No relevant documents found.",
            "sources": [],
        }

        mock_search.assert_called_once_with(
            db=fake_db,
            query="What is the capital of Australia?",
            organization_id=TEST_ORGANIZATION_ID,
            top_k=3,
        )

        mock_create.assert_not_called()
        rag_service.cache.set.assert_called_once()


@patch("app.rag.answer_generator.semantic_search")
def test_successful_answer(
    mock_search,
    rag_service,
):
    mock_search.return_value = [
        {
            "chunk_id": 1,
            "document_id": 10,
            "content": "Sprint 4 completed 13 story points.",
            "similarity": 0.85,
        }
    ]

    mock_response = MagicMock()
    mock_response.choices[0].message.content = (
        "Sprint 4 completed 13 story points. (Chunk 1)"
    )

    fake_db = MagicMock()

    with patch.object(
        rag_service.client.chat.completions,
        "create",
        return_value=mock_response,
    ) as mock_create:

        result = rag_service.generate_answer(
            db=fake_db,
            question="What went well in Sprint 4?",
            organization_id=TEST_ORGANIZATION_ID,
            top_k=1,
        )

        assert result["answer"] == (
            "Sprint 4 completed 13 story points. (Chunk 1)"
        )

        assert result["sources"] == [
            {
                "chunk_id": 1,
                "document_id": 10,
                "similarity": 0.85,
            }
        ]

        mock_search.assert_called_once_with(
            db=fake_db,
            query="What went well in Sprint 4?",
            organization_id=TEST_ORGANIZATION_ID,
            top_k=1,
        )

        mock_create.assert_called_once()
        rag_service.cache.set.assert_called_once()


@patch("app.rag.answer_generator.semantic_search")
def test_cache_hit(
    mock_search,
    rag_service,
):
    cached_answer = {
        "question": "What is RAG?",
        "answer": "RAG combines retrieval and generation.",
        "sources": [
            {
                "chunk_id": 5,
                "document_id": 2,
                "similarity": 0.92,
            }
        ],
    }

    rag_service.cache.get.return_value = cached_answer

    with patch.object(
        rag_service.client.chat.completions,
        "create",
    ) as mock_create:

        result = rag_service.generate_answer(
            db=MagicMock(),
            question="What is RAG?",
            organization_id=TEST_ORGANIZATION_ID,
            top_k=3,
        )

        assert result == cached_answer

        mock_search.assert_not_called()
        mock_create.assert_not_called()
        rag_service.cache.set.assert_not_called()


def test_invalid_top_k(rag_service):
    with pytest.raises(
        ValueError,
        match="top_k must be positive",
    ):
        rag_service.generate_answer(
            db=MagicMock(),
            question="What is RAG?",
            organization_id=TEST_ORGANIZATION_ID,
            top_k=0,
        )


def test_invalid_organization_id(rag_service):
    with pytest.raises(
        ValueError,
        match="Invalid organization ID",
    ):
        rag_service.generate_answer(
            db=MagicMock(),
            question="What is RAG?",
            organization_id=0,
            top_k=3,
        )
