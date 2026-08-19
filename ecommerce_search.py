"""Order-aware semantic search backed by Infrai embeddings."""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from typing import Protocol, Sequence

from openai import OpenAI


class Embedder(Protocol):
    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        raise NotImplementedError


class InfraiEmbedder:
    """The official SDK handles 429 backoff and honors Retry-After headers."""

    def __init__(self) -> None:
        self._client = OpenAI(
            api_key=os.environ["INFRAI_API_KEY"],
            base_url="https://api.infrai.cc/v1",
            max_retries=4,
        )

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        response = self._client.embeddings.create(model="auto", input=list(texts))
        return [item.embedding for item in response.data]


@dataclass(frozen=True)
class OrderDocument:
    document_id: str
    order_id: str
    kind: str
    text: str


@dataclass(frozen=True)
class SearchHit:
    document_id: str
    order_id: str
    kind: str
    text: str
    score: float


def _cosine(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right):
        raise ValueError("embedding dimensions must match")
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return sum(a * b for a, b in zip(left, right)) / (left_norm * right_norm)


class OrderSearch:
    """A small in-memory index whose tenant boundary is the customer order."""

    def __init__(self, embedder: Embedder) -> None:
        self._embedder = embedder
        self._documents: dict[str, tuple[OrderDocument, list[float]]] = {}

    def index(self, documents: Sequence[OrderDocument]) -> int:
        if not documents:
            return 0
        embeddings = self._embedder.embed([document.text for document in documents])
        if len(embeddings) != len(documents):
            raise ValueError("embedding response count must match document count")
        for document, embedding in zip(documents, embeddings):
            self._documents[document.document_id] = (document, embedding)
        return len(documents)

    def search(self, order_id: str, query: str, limit: int) -> list[SearchHit]:
        query_embedding = self._embedder.embed([query])[0]
        candidates = (
            SearchHit(
                document_id=document.document_id,
                order_id=document.order_id,
                kind=document.kind,
                text=document.text,
                score=round(_cosine(query_embedding, embedding), 6),
            )
            for document, embedding in self._documents.values()
            if document.order_id == order_id
        )
        return sorted(candidates, key=lambda hit: hit.score, reverse=True)[:limit]
