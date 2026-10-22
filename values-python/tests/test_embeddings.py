#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""本地哈希向量。"""

from __future__ import annotations

import math
import unittest

from food_nutrition.ai.rag.embeddings import HashingEmbedding, _tokenize


def _cosine(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


class HashingEmbeddingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.embedding = HashingEmbedding(dimension=128)

    def test_dimension_and_normalization(self) -> None:
        [vector] = self.embedding.embed_texts(["protein helps muscle growth"])

        self.assertEqual(len(vector), 128)
        self.assertAlmostEqual(math.sqrt(sum(value * value for value in vector)), 1.0, places=6)

    def test_is_deterministic(self) -> None:
        first = self.embedding.embed_texts(["维生素 C 的营养作用"])[0]
        second = self.embedding.embed_texts(["维生素 C 的营养作用"])[0]

        self.assertEqual(first, second)

    def test_empty_text_returns_zero_vector(self) -> None:
        [vector] = self.embedding.embed_texts(["   "])

        self.assertEqual(vector, [0.0] * 128)

    def test_related_text_scores_higher_than_unrelated(self) -> None:
        query = self.embedding.embed_texts(["protein function in body"])[0]
        related = self.embedding.embed_texts(["protein supports muscle and tissue repair"])[0]
        unrelated = self.embedding.embed_texts(["vitamin c supports immunity"])[0]

        self.assertGreater(_cosine(query, related), _cosine(query, unrelated))


class TokenizeTest(unittest.TestCase):
    def test_chinese_uses_bigrams(self) -> None:
        self.assertEqual(_tokenize("蛋白质"), ["蛋白", "白质"])

    def test_single_chinese_character_is_kept(self) -> None:
        self.assertEqual(_tokenize("钠"), ["钠"])

    def test_english_words_are_lowercased(self) -> None:
        self.assertEqual(_tokenize("Vitamin C"), ["vitamin", "c"])


if __name__ == "__main__":
    unittest.main()