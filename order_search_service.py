"""Runnable API for indexing and searching checkout and fulfillment events."""

from functools import lru_cache
from typing import Literal

from fastapi import Depends, FastAPI
from pydantic import BaseModel, Field

from ecommerce_search import InfraiEmbedder, OrderDocument, OrderSearch, SearchHit


DocumentKind = Literal["checkout", "fulfillment", "receipt", "customer_update"]


class DocumentInput(BaseModel):
    document_id: str = Field(min_length=1)
    order_id: str = Field(min_length=1)
    kind: DocumentKind
    text: str = Field(min_length=1)


class IndexRequest(BaseModel):
    documents: list[DocumentInput] = Field(min_length=1)


class IndexResult(BaseModel):
    indexed: int


class SearchRequest(BaseModel):
    order_id: str = Field(min_length=1)
    query: str = Field(min_length=1)
    limit: int = Field(default=3, ge=1, le=20)


class SearchResult(BaseModel):
    hits: list[SearchHit]


@lru_cache
def search_index() -> OrderSearch:
    return OrderSearch(InfraiEmbedder())


app = FastAPI(title="E-commerce order search")


@app.post("/documents", response_model=IndexResult)
def index_documents(
    request: IndexRequest, index: OrderSearch = Depends(search_index)
) -> IndexResult:
    documents = [OrderDocument(**document.model_dump()) for document in request.documents]
    return IndexResult(indexed=index.index(documents))


@app.post("/search", response_model=SearchResult)
def search_documents(
    request: SearchRequest, index: OrderSearch = Depends(search_index)
) -> SearchResult:
    hits = index.search(request.order_id, request.query, request.limit)
    return SearchResult(hits=hits)
