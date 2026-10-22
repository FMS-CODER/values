#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""进程内向量库与检索引用组装。"""

from __future__ import annotations

import unittest
from dataclasses import replace

from food_nutrition.ai.rag.chunker import KnowledgeDocument, chunk_document
from food_nutrition.ai.rag.embeddings import HashingEmbedding
from food_nutrition.ai.rag.retriever import Retriever
from food_nutrition.ai.rag.vector_store import MemoryVectorStore, VectorRecord
from food_nutrition.ai.settings import RagSettings


def _record(record_id: str, vector: list[float], doc_id: str, **payload) -> VectorRecord:
    return VectorRecord(
        id=record_id,
        vector=vector,
        payload={"chunk_id": record_id, "doc_id": doc_id, **payload},
    )


class MemoryVectorStoreTest(unittest.TestCase):
    def setUp(self) -> None:
        self.store = MemoryVectorStore()
        self.store.ensure_collection(2)

    def test_search_orders_by_similarity(self) -> None:
        self.store.upsert([
            _record("near", [1.0, 0.0], "doc:near"),
            _record("far", [0.0, 1.0], "doc:far"),
        ])

        hits = self.store.search([1.0, 0.0], limit=2)

        self.assertEqual([hit.id for hit in hits], ["near", "far"])
        self.assertAlmostEqual(hits[0].score, 1.0)

    def test_search_applies_payload_filters(self) -> None:
        self.store.upsert([
            _record("approved", [1.0, 0.0], "doc:a", review_status="approved"),
            _record("pending", [1.0, 0.0], "doc:b", review_status="pending"),
        ])

        hits = self.store.search([1.0, 0.0], limit=5, filters={"review_status": "approved"})

        self.assertEqual([hit.id for hit in hits], ["approved"])

    def test_upsert_same_id_replaces_record(self) -> None:
        self.store.upsert([_record("chunk", [1.0, 0.0], "doc:a", title="旧标题")])
        self.store.upsert([_record("chunk", [0.0, 1.0], "doc:a", title="新标题")])

        self.assertEqual(self.store.count(), 1)
        self.assertEqual(self.store.search([0.0, 1.0], limit=1)[0].payload["title"], "新标题")

    def test_delete_by_doc_removes_all_chunks(self) -> None:
        self.store.upsert([
            _record("a#0", [1.0, 0.0], "doc:a"),
            _record("a#1", [1.0, 0.0], "doc:a"),
            _record("b#0", [1.0, 0.0], "doc:b"),
        ])

        self.store.delete_by_doc("doc:a")

        self.assertEqual(self.store.count(), 1)

    def test_dimension_mismatch_is_rejected(self) -> None:
        with self.assertRaises(RuntimeError):
            self.store.ensure_collection(3)

    def test_recreate_clears_records(self) -> None:
        self.store.upsert([_record("a#0", [1.0, 0.0], "doc:a")])

        self.store.recreate(2)

        self.assertEqual(self.store.count(), 0)


class RetrieverTest(unittest.TestCase):
    def _settings(self) -> RagSettings:
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
            top_k=3,
            min_score=0.05,
            auto_index=False,
            knowledge_dir="unused",  # type: ignore[arg-type]
            include_pending=False,
        )

    def test_index_then_search_returns_citation(self) -> None:
        settings = self._settings()
        retriever = Retriever(
            store=MemoryVectorStore(),
            embedding=HashingEmbedding(settings.embedding_dim),
            settings=settings,
        )
        document = KnowledgeDocument(
            doc_id="nutrient:PROTEIN",
            title="蛋白质的营养作用",
            content="蛋白质参与组织修复、肌肉合成和免疫调节。",
            source="中国居民膳食营养素参考摄入量",
            source_url="https://example.org/protein",
            metadata={"nutrient_code": "PROTEIN"},
        )
        retriever.index(chunk_document(document))

        citations = retriever.search("蛋白质有什么作用？")

        self.assertTrue(citations)
        citation = citations[0]
        self.assertEqual(citation.document_id, "nutrient:PROTEIN")
        self.assertEqual(citation.title, "蛋白质的营养作用")
        self.assertEqual(citation.url, "https://example.org/protein")
        self.assertIn("组织修复", citation.snippet)
        self.assertEqual(citation.to_dict()["documentId"], "nutrient:PROTEIN")

    def test_search_skips_hits_below_min_score(self) -> None:
        # 哈希向量存在少量碰撞噪声，用较高阈值验证「低于 min_score 不进入引用」
        settings = replace(self._settings(), min_score=0.5)
        retriever = Retriever(
            store=MemoryVectorStore(),
            embedding=HashingEmbedding(settings.embedding_dim),
            settings=settings,
        )
        retriever.index(chunk_document(KnowledgeDocument(
            doc_id="nutrient:PROTEIN",
            title="蛋白质的营养作用",
            content="蛋白质参与组织修复。",
            source="测试",
        )))

        self.assertEqual(retriever.search("维生素C的抗氧化机制"), [])

    def test_blank_query_returns_empty(self) -> None:
        settings = self._settings()
        retriever = Retriever(
            store=MemoryVectorStore(),
            embedding=HashingEmbedding(settings.embedding_dim),
            settings=settings,
        )

        self.assertEqual(retriever.search("   "), [])


if __name__ == "__main__":
    unittest.main()