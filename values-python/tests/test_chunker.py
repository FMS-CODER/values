#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""知识文档清洗与切块。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from food_nutrition.ai.rag.chunker import (
    KnowledgeDocument,
    chunk_document,
    clean_text,
    load_markdown_document,
)


def _document(content: str, **kwargs) -> KnowledgeDocument:
    defaults = {
        "doc_id": "nutrient:PROTEIN",
        "title": "蛋白质的营养作用",
        "content": content,
        "source": "中国居民膳食营养素参考摄入量",
        "source_url": "https://example.org/protein",
        "version": "2",
        "review_status": "approved",
        "metadata": {"nutrient_code": "PROTEIN"},
    }
    defaults.update(kwargs)
    return KnowledgeDocument(**defaults)


class CleanTextTest(unittest.TestCase):
    def test_collapses_blank_lines_and_trailing_spaces(self) -> None:
        raw = "第一段  内容\t\n\n\n\n第二段\n"
        self.assertEqual(clean_text(raw), "第一段 内容\n\n第二段")

    def test_handles_windows_newlines(self) -> None:
        self.assertEqual(clean_text("甲\r\n乙"), "甲\n乙")


class ChunkDocumentTest(unittest.TestCase):
    def test_empty_content_produces_no_chunk(self) -> None:
        self.assertEqual(chunk_document(_document("   \n\n ")), [])

    def test_short_document_keeps_metadata_in_payload(self) -> None:
        chunks = chunk_document(_document("蛋白质参与肌肉合成。"))

        self.assertEqual(len(chunks), 1)
        payload = chunks[0].to_payload()
        self.assertEqual(payload["chunk_id"], "nutrient:PROTEIN#0")
        self.assertEqual(payload["doc_id"], "nutrient:PROTEIN")
        self.assertEqual(payload["nutrient_code"], "PROTEIN")
        self.assertEqual(payload["version"], "2")
        self.assertEqual(payload["review_status"], "approved")
        self.assertEqual(payload["kind"], "knowledge")
        self.assertEqual(payload["url"], "https://example.org/protein")

    def test_long_document_is_split_with_sequential_index(self) -> None:
        paragraph = "蛋白质由氨基酸构成，参与组织修复与免疫调节。" * 12
        chunks = chunk_document(_document("\n\n".join([paragraph] * 4)), max_chars=200, overlap=40)

        self.assertGreater(len(chunks), 1)
        self.assertEqual([chunk.chunk_index for chunk in chunks], list(range(len(chunks))))
        self.assertTrue(all(chunk.text.strip() for chunk in chunks))
        self.assertTrue(all(chunk.doc_id == "nutrient:PROTEIN" for chunk in chunks))

    def test_overlap_carries_context_between_neighbours(self) -> None:
        first = "甲" * 180
        second = "乙" * 180
        chunks = chunk_document(_document(f"{first}\n\n{second}"), max_chars=200, overlap=30)

        self.assertEqual(len(chunks), 2)
        # 第二块以第一块的尾部开头，避免答案刚好被切在边界上
        self.assertTrue(chunks[1].text.startswith("甲" * 30))

    def test_single_sentence_longer_than_limit_is_hard_split(self) -> None:
        chunks = chunk_document(_document("丙" * 520), max_chars=200, overlap=20)

        self.assertGreaterEqual(len(chunks), 3)
        self.assertTrue(all(len(chunk.text) <= 200 for chunk in chunks))


class MarkdownDocumentTest(unittest.TestCase):
    def test_reads_front_matter(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "protein.md"
            path.write_text(
                "---\n"
                "doc_id: file:protein\n"
                "title: 蛋白质入门\n"
                "source: 内部资料\n"
                "version: 3\n"
                "review_status: pending\n"
                "---\n\n"
                "# 正文标题\n\n蛋白质的基础说明。\n",
                encoding="utf-8",
            )

            document = load_markdown_document(path)

        self.assertEqual(document.doc_id, "file:protein")
        self.assertEqual(document.title, "蛋白质入门")
        self.assertEqual(document.version, "3")
        self.assertEqual(document.review_status, "pending")
        self.assertIn("蛋白质的基础说明。", document.content)

    def test_falls_back_to_first_heading_or_filename(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fiber.md"
            path.write_text("# 膳食纤维\n\n有助于肠道健康。\n", encoding="utf-8")

            document = load_markdown_document(path)

        self.assertEqual(document.title, "膳食纤维")
        self.assertEqual(document.doc_id, "file:fiber")
        self.assertEqual(document.source, "本地知识文档")


if __name__ == "__main__":
    unittest.main()