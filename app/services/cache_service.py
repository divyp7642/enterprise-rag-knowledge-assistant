
import json

from redis.exceptions import RedisError

from app.core.redis_client import redis_client


DEFAULT_CACHE_TTL = 300


class CacheService:

    def __init__(self):
        self.redis = redis_client

    def get(self, key: str):
        try:
            cached_data = self.redis.get(key)

            if cached_data is None:
                return None

            return json.loads(cached_data)

        except (RedisError, json.JSONDecodeError):
            return None

    def set(
        self,
        key: str,
        value: dict,
        ttl: int = DEFAULT_CACHE_TTL,
    ) -> bool:
        try:
            self.redis.set(
                name=key,
                value=json.dumps(value),
                ex=ttl,
            )
            return True

        except (RedisError, TypeError, ValueError):
            return False

    def delete(self, key: str) -> bool:
        try:
            self.redis.delete(key)
            return True

        except RedisError:
            return False

    def invalidate_rag_cache(
        self,
        organization_id: int | None = None,
    ) -> bool:
        """
        Invalidate cached RAG answers.

        When organization_id is provided,
        invalidate only that organization's cache.

        When organization_id is None,
        invalidate all RAG answer caches.
        """

        if organization_id is not None:
            if organization_id <= 0:
                raise ValueError(
                    "Invalid organization ID"
                )

            pattern = (
                f"rag:answer:org:{organization_id}:*"
            )
        else:
            pattern = "rag:answer:*"

        try:
            for key in self.redis.scan_iter(
                match=pattern,
                count=100,
            ):
                self.redis.delete(key)

            return True

        except RedisError:
            return False
