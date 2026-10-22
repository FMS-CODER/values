#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""统一知识检索入口。

Agent 不直接接触 Qdrant / embedding：
- 首次调用时按需建索引；
- 默认只召回 review_status=approved 的文档；
- 向量库异常时返回空证据，由回答层明确说明「没有找到依据」。
"""

from __future__ import annotations

import logging
import threading

from ..rag.ingestion import KnowledgeIngestionService, IndexStats
from ..rag.retriever import Citation, Retriever
from ..settings import RagSettings, load_rag

logger = logging.getLogger(__name__)


class KnowledgeService:
    _lock = threading.Lock()

    def __init__(
        self,
        *,
        retriever: Retriever | None = None,
        settings: RagSettings | None = None,
    ) -> None:
        self.settings = settings or load_rag()
        self.retriever = retriever or Retriever(settings=self.settings)
        self.ingestion = KnowledgeIngestionService(
            retriever=self.retriever,
            settings=self.settings,
        )
        self._indexed = False

    def search(
        self,
        query: str,
        *,
        top_k: int | None = None,
        nutrient_code: str | None = None,
    ) -> list[Citation]:
        self._ensure_indexed()
        base_filters: dict[str, str] = {}
        if not self.settings.include_pending:
            base_filters["review_status"] = "approved"

        try:
            if nutrient_code:
                citations = self.retriever.search(
                    query,
                    top_k=top_k,
                    filters={**base_filters, "nutrient_code": nutrient_code},
                )
                if citations:
                    return citations
            return self.retriever.search(query, top_k=top_k, filters=base_filters or None)
        except Exception as exc:
            # 检索失败不等于「没有知识」；记录真实原因，返回值保持为空让上层提示不确定性
            logger.warning("知识检索失败：%s", exc)
            return []

    def reindex(self, *, rebuild: bool = True) -> IndexStats:
        with self._lock:
            stats = self.ingestion.reindex(rebuild=rebuild)
            self._indexed = True
            return stats

    def _ensure_indexed(self) -> None:
        if self._indexed or not self.settings.auto_index:
            return
        with self._lock:
            if self._indexed:
                return
            self.ingestion.ensure_indexed()
            self._indexed = True