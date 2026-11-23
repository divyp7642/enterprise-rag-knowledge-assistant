
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.dependencies import get_current_user
from app.db.database import get_db
from app.main import app
from app.rag.answer_generator import RAGAnswerService


def fake_user(organization_id):
    return SimpleNamespace(
        id=organization_id,
        organization_id=organization_id,
    )


@pytest.fixture
def client():
    app.dependency_overrides[get_db] = lambda: MagicMock()

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_rag_requires_authentication(client):
    response = client.post(
        "/rag/ask",
        json={"question": "What is our policy?"},
    )

    assert response.status_code == 401


@patch("app.api.rag.RAGAnswerService")
def test_rag_uses_authenticated_organization(
    mock_service,
    client,
):
    app.dependency_overrides[get_current_user] = (
        lambda: fake_user(2)
    )

    mock_service.return_value.generate_answer.return_value = {
        "question": "What is our policy?",
        "answer": "Organization 2 policy.",
        "sources": [],
    }

    response = client.post(
        "/rag/ask",
        json={"question": "What is our policy?"},
    )

    assert response.status_code == 200

    kwargs = (
        mock_service.return_value.generate_answer
        .call_args.kwargs
    )

    assert kwargs["organization_id"] == 2
    assert kwargs["question"] == "What is our policy?"


@patch("app.api.rag.RAGAnswerService")
def test_rag_ignores_client_organization_id(
    mock_service,
    client,
):
    app.dependency_overrides[get_current_user] = (
        lambda: fake_user(2)
    )

    mock_service.return_value.generate_answer.return_value = {
        "question": "Company policy",
        "answer": "Organization 2 answer.",
        "sources": [],
    }

    response = client.post(
        "/rag/ask",
        json={
            "question": "Company policy",
            "organization_id": 1,
        },
    )

    assert response.status_code == 200

    kwargs = (
        mock_service.return_value.generate_answer
        .call_args.kwargs
    )

    assert kwargs["organization_id"] == 2


def test_different_organizations_have_different_cache_keys():
    service = RAGAnswerService.__new__(
        RAGAnswerService
    )

    key_org_1 = service._generate_cache_key(
        question="What is our policy?",
        organization_id=1,
        top_k=3,
    )

    key_org_2 = service._generate_cache_key(
        question="What is our policy?",
        organization_id=2,
        top_k=3,
    )

    assert key_org_1 != key_org_2
    assert key_org_1.startswith("rag:answer:org:1:")
    assert key_org_2.startswith("rag:answer:org:2:")


def test_invalid_organization_cache_key():
    service = RAGAnswerService.__new__(
        RAGAnswerService
    )

    with pytest.raises(
        ValueError,
        match="Invalid organization ID",
    ):
        service._generate_cache_key(
            question="Company policy",
            organization_id=0,
            top_k=3,
        )


@patch("app.rag.answer_generator.semantic_search")
def test_rag_search_uses_organization(
    mock_search,
):
    service = RAGAnswerService.__new__(
        RAGAnswerService
    )

    service.cache = MagicMock()
    service.cache.get.return_value = None

    mock_search.return_value = []

    result = service.generate_answer(
        db=MagicMock(),
        question="Company policy",
        organization_id=2,
        top_k=3,
    )

    assert result["answer"] == (
        "No relevant documents found."
    )

    assert (
        mock_search.call_args.kwargs["organization_id"]
        == 2
    )


@patch("app.rag.answer_generator.semantic_search")
def test_organizations_do_not_share_cached_answers(
    mock_search,
):
    service = RAGAnswerService.__new__(
        RAGAnswerService
    )

    service.cache = MagicMock()

    cached_answers = {}

    service.cache.get.side_effect = (
        lambda key: cached_answers.get(key)
    )

    service.cache.set.side_effect = (
        lambda key, value, ttl: cached_answers.update({
            key: value
        })
    )

    mock_search.return_value = []

    service.generate_answer(
        db=MagicMock(),
        question="Company policy",
        organization_id=1,
    )

    service.generate_answer(
        db=MagicMock(),
        question="Company policy",
        organization_id=2,
    )

    assert len(cached_answers) == 2

    assert any(
        key.startswith("rag:answer:org:1:")
        for key in cached_answers
    )

    assert any(
        key.startswith("rag:answer:org:2:")
        for key in cached_answers
    )

    assert mock_search.call_count == 2
