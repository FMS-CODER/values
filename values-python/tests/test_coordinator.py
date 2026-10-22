#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""问题类型识别。"""

from __future__ import annotations

import unittest

from food_nutrition.ai.agents.coordinator import Coordinator
from food_nutrition.ai.agents.nutrition_data_agent import DataResult


def _data(*, foods=None, nutrient: str | None = None) -> DataResult:
    return DataResult(
        answer="",
        context="",
        foods=foods or [],
        nutrient=nutrient,
    )


class CoordinatorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.coordinator = Coordinator()

    def test_two_foods_use_both_sources(self) -> None:
        plan = self.coordinator.plan("西兰花和菠菜哪个更好？", _data(foods=[{"name": "西兰花"}, {"name": "菠菜"}]))

        self.assertEqual(plan.intent, "food_comparison")
        self.assertTrue(plan.use_data)
        self.assertTrue(plan.use_knowledge)
        self.assertTrue(plan.use_llm)
        self.assertTrue(plan.review)

    def test_food_detail_without_knowledge_question_skips_llm(self) -> None:
        plan = self.coordinator.plan("西兰花的热量是多少？", _data(foods=[{"name": "西兰花"}]))

        self.assertEqual(plan.intent, "food_detail")
        self.assertTrue(plan.use_data)
        self.assertFalse(plan.use_knowledge)
        self.assertFalse(plan.use_llm)
        self.assertFalse(plan.review)

    def test_food_detail_with_knowledge_question_enables_review(self) -> None:
        plan = self.coordinator.plan("西兰花有什么营养作用？", _data(foods=[{"name": "西兰花"}]))

        self.assertEqual(plan.intent, "food_detail")
        self.assertTrue(plan.use_knowledge)
        self.assertTrue(plan.use_llm)
        self.assertTrue(plan.review)

    def test_nutrient_ranking_uses_sql_only(self) -> None:
        plan = self.coordinator.plan("哪些食物蛋白质含量最高？", _data(nutrient="PROTEIN"))

        self.assertEqual(plan.intent, "nutrient_ranking")
        self.assertTrue(plan.use_data)
        self.assertFalse(plan.use_knowledge)
        self.assertFalse(plan.use_llm)

    def test_nutrient_knowledge_question_skips_sql(self) -> None:
        plan = self.coordinator.plan("蛋白质有什么作用？", _data(nutrient="PROTEIN"))

        self.assertEqual(plan.intent, "knowledge")
        self.assertFalse(plan.use_data)
        self.assertTrue(plan.use_knowledge)
        self.assertTrue(plan.use_llm)
        self.assertTrue(plan.review)

    def test_nutrient_with_analysis_words_uses_both_sources(self) -> None:
        plan = self.coordinator.plan("减脂期间蛋白质怎么吃？", _data(nutrient="PROTEIN"))

        self.assertEqual(plan.intent, "analysis")
        self.assertTrue(plan.use_data)
        self.assertTrue(plan.use_knowledge)
        self.assertTrue(plan.use_llm)

    def test_no_entity_analysis_uses_knowledge_only(self) -> None:
        plan = self.coordinator.plan("减脂期间的饮食建议", _data())

        self.assertEqual(plan.intent, "analysis")
        self.assertFalse(plan.use_data)
        self.assertTrue(plan.use_knowledge)
        self.assertTrue(plan.review)

    def test_general_question_uses_no_source(self) -> None:
        plan = self.coordinator.plan("你好", _data())

        self.assertEqual(plan.intent, "general")
        self.assertFalse(plan.use_data)
        self.assertFalse(plan.use_knowledge)
        self.assertFalse(plan.use_llm)
        self.assertFalse(plan.review)


if __name__ == "__main__":
    unittest.main()