
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536


class EmbeddingService:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY is missing from .env"
            )

        self.client = OpenAI(api_key=api_key)

    def generate_embeddings(
        self,
        texts: list[str]
    ) -> list[list[float]]:
        if not texts:
            return []

        if any(not text.strip() for text in texts):
            raise ValueError(
                "Cannot generate embeddings for empty text"
            )

        response = self.client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=texts,
            dimensions=EMBEDDING_DIMENSIONS
        )

        ordered = sorted(
            response.data,
            key=lambda item: item.index
        )

        embeddings = [
            item.embedding
            for item in ordered
        ]

        if len(embeddings) != len(texts):
            raise RuntimeError(
                "Unexpected number of embeddings returned"
            )

        return embeddings
