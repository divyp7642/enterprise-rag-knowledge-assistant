
import json
from unittest.mock import MagicMock

import pytest
from redis.exceptions import ConnectionError

from app.services.cache_service import CacheService


@pytest.fixture
def cache_service():
    service = CacheService()
    service.redis = MagicMock()
    return service


def test_cache_set(cache_service):
    data = {"answer": "RAG uses retrieval."}

    result = cache_service.set(
        key="rag:test",
        value=data,
        ttl=60
    )

    assert result is True

    cache_service.redis.set.assert_called_once_with(
        name="rag:test",
        value=json.dumps(data),
        ex=60
    )


def test_cache_get(cache_service):
    data = {"answer": "Cached response"}

    cache_service.redis.get.return_value = (
        json.dumps(data)
    )

    result = cache_service.get("rag:test")

    assert result == data


def test_cache_miss(cache_service):
    cache_service.redis.get.return_value = None

    result = cache_service.get("rag:missing")

    assert result is None


def test_cache_delete(cache_service):
    result = cache_service.delete("rag:test")

    assert result is True

    cache_service.redis.delete.assert_called_once_with(
        "rag:test"
    )


def test_cache_connection_failure(cache_service):
    cache_service.redis.get.side_effect = (
        ConnectionError("Redis unavailable")
    )

    result = cache_service.get("rag:test")

    assert result is None


def test_cache_ttl(cache_service):
    cache_service.set(
        key="rag:ttl",
        value={"answer": "Temporary"},
        ttl=120
    )

    assert (
        cache_service.redis.set.call_args.kwargs["ex"]
        == 120
    )


def test_invalidate_rag_cache(cache_service):
    cache_service.redis.scan_iter.return_value = iter([
        "rag:answer:abc123",
        "rag:answer:def456"
    ])

    result = cache_service.invalidate_rag_cache()

    assert result is True

    cache_service.redis.scan_iter.assert_called_once_with(
        match="rag:answer:*",
        count=100
    )

    assert cache_service.redis.delete.call_count == 2

    cache_service.redis.delete.assert_any_call(
        "rag:answer:abc123"
    )

    cache_service.redis.delete.assert_any_call(
        "rag:answer:def456"
    )


def test_invalidate_empty_cache(cache_service):
    cache_service.redis.scan_iter.return_value = iter([])

    result = cache_service.invalidate_rag_cache()

    assert result is True

    cache_service.redis.delete.assert_not_called()


def test_invalidate_redis_failure(cache_service):
    cache_service.redis.scan_iter.side_effect = (
        ConnectionError("Redis unavailable")
    )

    result = cache_service.invalidate_rag_cache()

    assert result is False
