#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""统一问答流程。

流程固定为：
  实体识别 → 计划 → SQL / RAG（可并行）→ 合成 → 审核 → 返回

入口保持在 ChatService.answer，HTTP 层只负责参数校验与序列化。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from ..agents.answer_reviewer import AnswerReviewer
from ..agents.coordinator import Coordinator, Plan
from ..agents.knowledge_agent import KnowledgeAgent, KnowledgeResult
from ..agents.nutrition_analysis_agent import NutritionAnalysisAgent
from ..agents.nutrition_data_agent import DataResult, NutritionDataAgent
from ..rag.retriever import Citation

logger = logging.getLogger(__name__)

SUGGESTIONS = [
    "西兰花有哪些营养亮点？",
    "高蛋白的食物有哪些？",
    "维生素 C 有哪些营养作用？",
]


@dataclass
class ChatResult:
    reply: str
    mode: str
    suggestions: list[str] = field(default_factory=list)
    citations: list[Citation] = field(default_factory=list)
    intent: str = "general"


class ChatService:
    def __init__(
        self,
        *,
        data_agent: NutritionDataAgent | None = None,
        knowledge_agent: KnowledgeAgent | None = None,
        analysis_agent: NutritionAnalysisAgent | None = None,
        reviewer: AnswerReviewer | None = None,
        coordinator: Coordinator | None = None,
    ) -> None:
        self.data_agent = data_agent or NutritionDataAgent()
        self.knowledge_agent = knowledge_agent or KnowledgeAgent()
        self.analysis_agent = analysis_agent or NutritionAnalysisAgent()
        self.reviewer = reviewer or AnswerReviewer()
        self.coordinator = coordinator or Coordinator()

    def answer(
        self,
        message: str,
        history: list[dict[str, str]] | None = None,
    ) -> ChatResult:
        history = history or []
        data = self.data_agent.inspect(message)
        plan = self.coordinator.plan(message, data)

        if plan.intent == "general":
            return ChatResult(
                reply=data.answer,
                mode="database",
                suggestions=SUGGESTIONS,
                citations=[],
                intent=plan.intent,
            )

        knowledge = self._knowledge(message, plan, data.nutrient)
        citations = _merge_citations(
            data.citations if plan.use_data else [],
            knowledge.citations,
        )

        if plan.use_llm:
            analysis = self.analysis_agent.compose(
                message=message,
                history=history,
                data_answer=data.answer if plan.use_data else "",
                data_context=data.context if plan.use_data else "",
                knowledge=knowledge,
            )
            review = self.reviewer.review(
                reply=analysis.reply,
                mode=analysis.mode,
                data_context=f"{data.context}\n\n{knowledge.context}",
                citations=citations,
            )
            if review.approved:
                return ChatResult(
                    reply=analysis.reply,
                    mode=analysis.mode,
                    suggestions=SUGGESTIONS,
                    citations=citations,
                    intent=plan.intent,
                )

            logger.warning("答案审核未通过：%s", "；".join(review.issues))
            reply = self.analysis_agent.fallback(
                data.answer if plan.use_data else "",
                knowledge,
            )
            return ChatResult(
                reply=reply,
                mode="database" if (plan.use_data and data.answer) else "rag",
                suggestions=SUGGESTIONS,
                citations=citations,
                intent=plan.intent,
            )

        if plan.use_data:
            return ChatResult(
                reply=data.answer,
                mode="database",
                suggestions=SUGGESTIONS,
                citations=citations,
                intent=plan.intent,
            )

        if knowledge.has_evidence:
            return ChatResult(
                reply=knowledge.fallback_answer(),
                mode="rag",
                suggestions=SUGGESTIONS,
                citations=citations,
                intent=plan.intent,
            )

        return ChatResult(
            reply=self._uncertainty(),
            mode="rag",
            suggestions=SUGGESTIONS,
            citations=[],
            intent=plan.intent,
        )

    def _knowledge(
        self,
        message: str,
        plan: Plan,
        nutrient_code: str | None,
    ) -> KnowledgeResult:
        if not plan.use_knowledge:
            return KnowledgeResult()
        return self.knowledge_agent.search(message, nutrient_code=nutrient_code)

    @staticmethod
    def _uncertainty() -> str:
        return (
            "没有检索到足以回答这个问题的数据或知识库依据。\n"
            "可以补充具体的食物、营养素名称，或换一种问法后再试。"
        )


def _merge_citations(*groups: list[Citation]) -> list[Citation]:
    merged: list[Citation] = []
    seen: set[str] = set()
    for group in groups:
        for citation in group:
            if citation.document_id in seen:
                continue
            seen.add(citation.document_id)
            merged.append(citation)
    return merged