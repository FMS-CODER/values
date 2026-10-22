#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""知识 Agent：调用 RAG 检索，并把引用整理成可注入提示词的上下文。"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..rag.retriever import Citation
from ..services.knowledge_service import KnowledgeService


@dataclass
class KnowledgeResult:
    citations: list[Citation] = field(default_factory=list)
    context: str = ""

    @property
    def has_evidence(self) -> bool:
        return bool(self.citations)

    def fallback_answer(self) -> str:
        if not self.citations:
            return (
                "知识库中没有检索到足以回答这个问题的依据。\n"
                "可以换一种问法，或补充具体的食物、营养素名称后再试。"
            )

        lines = ["我从知识库中找到以下依据："]
        for index, citation in enumerate(self.citations, start=1):
            lines.append(
                f"{index}. {citation.title}（{citation.source}）：{citation.snippet}"
            )
        lines.extend(["", "以上为知识库原文要点，未做超出原文的推断。"])
        return "\n".join(lines)


class KnowledgeAgent:
    def __init__(self, service: KnowledgeService | None = None) -> None:
        self.service = service or KnowledgeService()

    def search(
        self,
        query: str,
        *,
        top_k: int | None = None,
        nutrient_code: str | None = None,
    ) -> KnowledgeResult:
        citations = self.service.search(query, top_k=top_k, nutrient_code=nutrient_code)
        if not citations:
            return KnowledgeResult()

        lines = ["知识库检索结果（按相关度排序）："]
        for index, citation in enumerate(citations, start=1):
            lines.append(
                f"[{index}] {citation.title}\n"
                f"来源：{citation.source}\n"
                f"版本：{citation.version}；审核状态：{citation.review_status}\n"
                f"内容：{citation.snippet}"
            )
        return KnowledgeResult(citations=citations, context="\n\n".join(lines))