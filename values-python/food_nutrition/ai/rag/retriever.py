#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""向量召回与引用组装。"""

from __future__ import annotations

import argparse
import logging
from dataclasses import dataclass
from typing import Any

from .chunker import Chunk
from .embeddings import EmbeddingModel, create_embedding
from .vector_store import VectorRecord, VectorStore, create_vector_store
from ..settings import RagSettings, load_rag

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Citation:
    document_id: str
    title: str
    source: str
    url: str
    snippet: str
    score: float
    kind: str = "knowledge"
    review_status: str = "approved"
    version: str = "1"

    def to_dict(self) -> dict[str, Any]:
        return {
            "documentId": self.document_id,
            "title": self.title,
            "source": self.source,
            "url": self.url,
            "snippet": self.snippet,
            "score": self.score,
            "kind": self.kind,
            "reviewStatus": self.review_status,
            "version": self.version,
        }


class Retriever:
    def __init__(
        self,
        *,
        store: VectorStore | None = None,
        embedding: EmbeddingModel | None = None,
        settings: RagSettings | None = None,
    ) -> None:
        self.settings = settings or load_rag()
        self.store = store or create_vector_store()
        self.embedding = embedding or create_embedding(self.settings)

    def index(self, chunks: list[Chunk]) -> int:
        if not chunks:
            return 0
        self.store.ensure_collection(self.embedding.dimension)
        vectors = self.embedding.embed_texts([chunk.embedding_text() for chunk in chunks])
        records = [
            VectorRecord(
                id=chunk.chunk_id,
                vector=vector,
                payload=chunk.to_payload(),
            )
            for chunk, vector in zip(chunks, vectors)
        ]
        self.store.upsert(records)
        return len(records)

    def recreate(self, chunks: list[Chunk]) -> int:
        self.store.recreate(self.embedding.dimension)
        return self.index(chunks)

    def delete_document(self, doc_id: str) -> None:
        self.store.delete_by_doc(doc_id)

    def search(
        self,
        query: str,
        *,
        top_k: int | None = None,
        filters: dict[str, Any] | None = None,
    ) -> list[Citation]:
        if not query.strip():
            return []
        top_k = top_k or self.settings.top_k
        vector = self.embedding.embed_texts([query])[0]
        hits = self.store.search(vector, limit=top_k, filters=filters)

        citations: list[Citation] = []
        for hit in hits:
            if hit.score < self.settings.min_score:
                continue
            payload = hit.payload
            citations.append(
                Citation(
                    document_id=str(payload.get("doc_id") or hit.id),
                    title=str(payload.get("title") or "未命名知识"),
                    source=str(payload.get("source") or "未知来源"),
                    url=str(payload.get("url") or ""),
                    snippet=_snippet(str(payload.get("text") or "")),
                    score=round(float(hit.score), 4),
                    kind=str(payload.get("kind") or "knowledge"),
                    review_status=str(payload.get("review_status") or "approved"),
                    version=str(payload.get("version") or "1"),
                )
            )
        return citations


def _snippet(text: str, limit: int = 220) -> str:
    cleaned = " ".join(text.split())
    return cleaned if len(cleaned) <= limit else f"{cleaned[:limit]}…"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="检索营养知识库")
    parser.add_argument("query", help="检索问题")
    parser.add_argument("--top-k", type=int, default=4)
    args = parser.parse_args(argv)

    from .. import retrieval
    from ..services.knowledge_service import KnowledgeService

    service = KnowledgeService()
    nutrient = retrieval.detect_nutrient(args.query)
    for citation in service.search(args.query, top_k=args.top_k, nutrient_code=nutrient):
        print(f"[{citation.score:.3f}] {citation.title} · {citation.source}")
        print(f"  {citation.snippet}")
        if citation.url:
            print(f"  {citation.url}")


if __name__ == "__main__":
    main()