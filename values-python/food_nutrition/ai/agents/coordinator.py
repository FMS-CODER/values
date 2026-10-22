#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""问题类型识别与执行计划。

第一版使用显式规则，不引入 LangGraph：
当前流程只有「查数据 / 查知识 / 两者合并」几条分支，状态可以一次性算完，
用规则表比引入状态机更容易审查。等需要跨请求恢复或复杂条件分支时再升级。
"""

from __future__ import annotations

from dataclasses import dataclass

from .nutrition_data_agent import DataResult

RANKING_WORDS = ("含量", "最高", "最低", "排名", "哪些食物", "推荐", "富含", "比较多", "较少")
KNOWLEDGE_WORDS = ("作用", "为什么", "是什么", "好处", "影响", "原理", "功能", "帮助", "意义", "解释")
ANALYSIS_WORDS = ("建议", "减脂", "减肥", "儿童", "孕妇", "糖尿病", "高血压", "怎么吃", "搭配", "饮食")


@dataclass(frozen=True)
class Plan:
    intent: str
    use_data: bool
    use_knowledge: bool
    use_llm: bool
    review: bool


class Coordinator:
    def plan(self, message: str, data: DataResult) -> Plan:
        if len(data.foods) >= 2:
            return Plan(
                intent="food_comparison",
                use_data=True,
                use_knowledge=True,
                use_llm=True,
                review=True,
            )

        if data.foods:
            asks_knowledge = _contains(message, KNOWLEDGE_WORDS)
            return Plan(
                intent="food_detail",
                use_data=True,
                use_knowledge=asks_knowledge,
                use_llm=asks_knowledge,
                review=asks_knowledge,
            )

        if data.nutrient:
            if _contains(message, ANALYSIS_WORDS):
                return Plan(
                    intent="analysis",
                    use_data=True,
                    use_knowledge=True,
                    use_llm=True,
                    review=True,
                )
            if _contains(message, RANKING_WORDS) or "食物" in message:
                return Plan(
                    intent="nutrient_ranking",
                    use_data=True,
                    use_knowledge=False,
                    use_llm=False,
                    review=False,
                )
            if _contains(message, KNOWLEDGE_WORDS):
                return Plan(
                    intent="knowledge",
                    use_data=False,
                    use_knowledge=True,
                    use_llm=True,
                    review=True,
                )
            return Plan(
                intent="nutrient_ranking",
                use_data=True,
                use_knowledge=False,
                use_llm=False,
                review=False,
            )

        if _contains(message, ANALYSIS_WORDS):
            return Plan(
                intent="analysis",
                use_data=False,
                use_knowledge=True,
                use_llm=True,
                review=True,
            )
        if _contains(message, KNOWLEDGE_WORDS):
            return Plan(
                intent="knowledge",
                use_data=False,
                use_knowledge=True,
                use_llm=True,
                review=True,
            )
        return Plan(
            intent="general",
            use_data=False,
            use_knowledge=False,
            use_llm=False,
            review=False,
        )


def _contains(message: str, words: tuple[str, ...]) -> bool:
    return any(word in message for word in words)