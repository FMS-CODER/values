#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""向量库封装。

业务代码只依赖 VectorStore 协议，不直接 import qdrant_client：
- 生产/联调默认使用 Qdrant；
- Qdrant 未启动、客户端未安装或测试环境使用 MemoryVectorStore。

这样即使向量库暂时不可用，AI 服务仍能启动；检索会降级为空证据，
由回答层明确告知「没有找到依据」，而不是让整个接口 500。
"""

from __future__ import annotations

import logging
import threading
import uuid
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Protocol

from ..settings import load_rag

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class VectorRecord:
    id: str
    vector: list[float]
    payload: dict[str, Any]


@dataclass(frozen=True)
class SearchHit:
    id: str
    score: float
    payload: dict[str, Any]


class VectorStore(Protocol):
    def ensure_collection(self, dimension: int) -> None:
        ...

    def recreate(self, dimension: int) -> None:
        ...

    def upsert(self, records: list[VectorRecord]) -> None:
        ...

    def search(
        self,
        vector: list[float],
        *,
        limit: int,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchHit]:
        ...

    def delete_by_doc(self, doc_id: str) -> None:
        ...

    def count(self) -> int:
        ...


class MemoryVectorStore:
    """进程内向量库，仅用于离线开发、单元测试和 Qdrant 不可用时的降级。"""

    def __init__(self) -> None:
        self._records: dict[str, VectorRecord] = {}
        self._dimension: int | None = None
        self._lock = threading.Lock()

    def ensure_collection(self, dimension: int) -> None:
        with self._lock:
            if self._dimension is None:
                self._dimension = dimension
            elif self._dimension != dimension:
                raise RuntimeError(
                    f"内存索引维度不一致：已有 {self._dimension}，当前 {dimension}；请重建索引"
                )

    def recreate(self, dimension: int) -> None:
        with self._lock:
            self._records.clear()
            self._dimension = dimension

    def upsert(self, records: list[VectorRecord]) -> None:
        with self._lock:
            for record in records:
                self._records[record.id] = record

    def search(
        self,
        vector: list[float],
        *,
        limit: int,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchHit]:
        with self._lock:
            candidates = list(self._records.values())

        hits = [
            SearchHit(id=record.id, score=_cosine(vector, record.vector), payload=record.payload)
            for record in candidates
            if _matches(record.payload, filters)
        ]
        hits.sort(key=lambda hit: hit.score, reverse=True)
        return hits[:limit]

    def delete_by_doc(self, doc_id: str) -> None:
        with self._lock:
            self._records = {
                key: record
                for key, record in self._records.items()
                if record.payload.get("doc_id") != doc_id
            }

    def count(self) -> int:
        with self._lock:
            return len(self._records)


class QdrantVectorStore:
    """Qdrant 实现。客户端与模型对象延迟导入，避免未安装时影响服务启动。"""

    def __init__(self, *, url: str, collection: str, api_key: str | None = None) -> None:
        from qdrant_client import QdrantClient

        self._client = QdrantClient(url=url, api_key=api_key, timeout=5)
        self._collection = collection

    def ping(self) -> None:
        self._client.get_collections()

    def ensure_collection(self, dimension: int) -> None:
        from qdrant_client.models import Distance, VectorParams

        if not self._client.collection_exists(self._collection):
            self._client.create_collection(
                collection_name=self._collection,
                vectors_config=VectorParams(size=dimension, distance=Distance.COSINE),
            )
            return

        info = self._client.get_collection(self._collection)
        vectors = info.config.params.vectors
        size = getattr(vectors, "size", None)
        if size is None and isinstance(vectors, dict):
            size = next(iter(vectors.values())).size
        if size is not None and int(size) != dimension:
            raise RuntimeError(
                f"Qdrant collection 维度为 {size}，当前嵌入维度为 {dimension}；"
                "请执行 python -m food_nutrition rag-index --rebuild"
            )

    def recreate(self, dimension: int) -> None:
        from qdrant_client.models import Distance, VectorParams

        if self._client.collection_exists(self._collection):
            self._client.delete_collection(self._collection)
        self._client.create_collection(
            collection_name=self._collection,
            vectors_config=VectorParams(size=dimension, distance=Distance.COSINE),
        )

    def upsert(self, records: list[VectorRecord]) -> None:
        from qdrant_client.models import PointStruct

        points = [
            PointStruct(
                id=str(uuid.uuid5(uuid.NAMESPACE_URL, record.id)),
                vector=record.vector,
                payload={**record.payload, "chunk_id": record.id},
            )
            for record in records
        ]
        if points:
            self._client.upsert(collection_name=self._collection, points=points)

    def search(
        self,
        vector: list[float],
        *,
        limit: int,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchHit]:
        query_filter = _qdrant_filter(filters)

        # qdrant-client 1.15 起推荐 query_points，旧版本仍只有 search；
        # 这里先走兼容层，避免锁死某一个客户端小版本。
        try:
            hits = self._client.search(
                collection_name=self._collection,
                query_vector=vector,
                limit=limit,
                query_filter=query_filter,
                with_payload=True,
            )
        except (AttributeError, TypeError):
            result = self._client.query_points(
                collection_name=self._collection,
                query=vector,
                limit=limit,
                query_filter=query_filter,
                with_payload=True,
            )
            hits = result.points

        return [
            SearchHit(
                id=(hit.payload or {}).get("chunk_id", str(hit.id)),
                score=float(hit.score),
                payload=hit.payload or {},
            )
            for hit in hits
        ]

    def delete_by_doc(self, doc_id: str) -> None:
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        self._client.delete(
            collection_name=self._collection,
            points_selector=Filter(
                must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]
            ),
        )

    def count(self) -> int:
        return int(self._client.count(collection_name=self._collection, exact=True).count)


@lru_cache(maxsize=1)
def create_vector_store() -> VectorStore:
    settings = load_rag()
    if settings.qdrant_enabled:
        try:
            store = QdrantVectorStore(
                url=settings.qdrant_url,
                collection=settings.collection,
                api_key=settings.qdrant_api_key,
            )
            store.ping()
            logger.info("使用 Qdrant 向量库：%s/%s", settings.qdrant_url, settings.collection)
            return store
        except Exception as exc:
            logger.warning("Qdrant 不可用，降级为进程内向量库：%s", exc)
    return MemoryVectorStore()


def _matches(payload: dict[str, Any], filters: dict[str, Any] | None) -> bool:
    if not filters:
        return True
    return all(payload.get(key) == value for key, value in filters.items())


def _cosine(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        return 0.0
    return float(sum(a * b for a, b in zip(left, right)))


def _qdrant_filter(filters: dict[str, Any] | None):
    if not filters:
        return None
    from qdrant_client.models import FieldCondition, Filter, MatchValue

    return Filter(
        must=[
            FieldCondition(key=key, match=MatchValue(value=value))
            for key, value in filters.items()
        ]
    )