#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""答案审核：拦截无引用回答和上下文之外的数值。"""

from __future__ import annotations

import unittest

from food_nutrition.ai.agents.answer_reviewer import AnswerReviewer
from food_nutrition.ai.rag.retriever import Citation


def _citation() -> Citation:
    return Citation(
        document_id="nutrient:PROTEIN",
        title="蛋白质的营养作用",
        source="测试来源",
        url="",
        snippet="蛋白质参与组织修复。",
        score=0.9,
    )


class AnswerReviewerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.reviewer = AnswerReviewer()

    def test_deterministic_answer_is_not_reviewed(self) -> None:
        result = self.reviewer.review(
            reply="西兰花每 100g 含蛋白质 2.8g。",
            mode="database",
            data_context="",
            citations=[],
        )

        self.assertTrue(result.approved)

    def test_llm_answer_without_citation_is_rejected(self) -> None:
        result = self.reviewer.review(
            reply="蛋白质有助于肌肉合成。",
            mode="llm",
            data_context="",
            citations=[],
        )

        self.assertFalse(result.approved)
        self.assertTrue(any("引用" in issue for issue in result.issues))

    def test_invented_value_is_rejected(self) -> None:
        result = self.reviewer.review(
            reply="每 100g 含蛋白质 99g。",
            mode="llm",
            data_context="西兰花：蛋白质 2.8g / 100g",
            citations=[_citation()],
        )

        self.assertFalse(result.approved)
        self.assertTrue(any("99" in issue for issue in result.issues))

    def test_value_from_context_passes(self) -> None:
        result = self.reviewer.review(
            reply="每 100g 西兰花含蛋白质 2.8g，可作为日常蔬菜选择。",
            mode="llm",
            data_context="西兰花：蛋白质 2.8g / 100g",
            citations=[_citation()],
        )

        self.assertTrue(result.approved, result.issues)

    def test_unit_alias_is_treated_as_same_family(self) -> None:
        result = self.reviewer.review(
            reply="每 100g 含蛋白质 2.8克。",
            mode="llm",
            data_context="西兰花：蛋白质 2.8g / 100g",
            citations=[_citation()],
        )

        self.assertTrue(result.approved, result.issues)

    def test_placeholder_copy_is_rejected(self) -> None:
        result = self.reviewer.review(
            reply="该能力尚未接入。",
            mode="llm",
            data_context="",
            citations=[_citation()],
        )

        self.assertFalse(result.approved)
        self.assertTrue(any("占位" in issue for issue in result.issues))


if __name__ == "__main__":
    unittest.main()