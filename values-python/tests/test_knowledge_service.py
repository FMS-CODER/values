#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""统一知识检索入口的过滤与降级。"""

from __future__ import annotations

import unittest
from typing import Any

from food_nutrition.ai.rag.retriever import Citation
from food_nutrition.ai.services.knowledge_service import KnowledgeService
from food_nutrition.ai.settings import RagSettings


def _settings(*, include_pending: bool = False) -> RagSettings:
    return RagSettings(
        qdrant_enabled=False,
        qdrant_url="http://127.0.0.1:6333",
        qdrant_api_key=None,
        collection="test",
        embedding_provider="hash",
        embedding_model="hash-ngram-v1",
        embedding_dim=384,
        embedding_base_url="",
        embedding_api_key_env="OPENAI_API_KEY",
        top_k=4,
        min_score=0.2,
        auto_index=False,
        knowledge_dir="unused",  # type: ignore[arg-type]
        include_pending=include_pending,
    )


class _FakeRetriever:
    def __init__(self, results: list[list[Citation]] | None = None, error: Exception | None = None) -> None:
        self.calls: list[dict[str, Any]] = []
        self._results = list(results or [])
        self._error = error

    def search(self, query: str, *, top_k: int | None = None, filters: dict[str, Any] | None = None):
        self.calls.append({"query": query, "top_k": top_k, "filters": filters})
        if self._error is not None:
            raise self._error
        if self._results:
            return self._results.pop(0)
        return []


def _citation(document_id: str) -> Citation:
    return Citation(
        document_id=document_id,
        title="测试知识",
        source="测试来源",
        url="",
        snippet="内容",
        score=0.8,
    )


class KnowledgeServiceTest(unittest.TestCase):
    def test_defaults_to_approved_documents(self) -> None:
        retriever = _FakeRetriever(results=[[_citation("nutrient:PROTEIN")]])
        service = KnowledgeService(retriever=retriever, settings=_settings())  # type: ignore[arg-type]

        citations = service.search("蛋白质有什么作用？")

        self.assertEqual(len(citations), 1)
        self.assertEqual(retriever.calls[0]["filters"], {"review_status": "approved"})

    def test_nutrient_filter_falls_back_to_whole_index(self) -> None:
        retriever = _FakeRetriever(results=[[], [_citation("nutrient:VITAMIN_C")]])
        service = KnowledgeService(retriever=retriever, settings=_settings())  # type: ignore[arg-type]

        citations = service.search("维生素 C 的作用", nutrient_code="VITAMIN_C")

        self.assertEqual(citations[0].document_id, "nutrient:VITAMIN_C")
        self.assertEqual(
            retriever.calls[0]["filters"],
            {"review_status": "approved", "nutrient_code": "VITAMIN_C"},
        )
        self.assertEqual(retriever.calls[1]["filters"], {"review_status": "approved"})

    def test_nutrient_filter_short_circuits_when_hit(self) -> None:
        retriever = _FakeRetriever(results=[[_citation("nutrient:PROTEIN")]])
        service = KnowledgeService(retriever=retriever, settings=_settings())  # type: ignore[arg-type]

        service.search("蛋白质的作用", nutrient_code="PROTEIN")

        self.assertEqual(len(retriever.calls), 1)

    def test_include_pending_removes_review_filter(self) -> None:
        retriever = _FakeRetriever(results=[[_citation("file:draft")]])
        service = KnowledgeService(
            retriever=retriever,
            settings=_settings(include_pending=True),
        )  # type: ignore[arg-type]

        service.search("任意问题")

        self.assertIsNone(retriever.calls[0]["filters"])

    def test_retrieval_error_degrades_to_empty_evidence(self) -> None:
        retriever = _FakeRetriever(error=RuntimeError("Qdrant 连接失败"))
        service = KnowledgeService(retriever=retriever, settings=_settings())  # type: ignore[arg-type]

        self.assertEqual(service.search("蛋白质的作用"), [])


if __name__ == "__main__":
    unittest.main()