#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""营养分析 Agent：把 SQL 数值与 RAG 知识合成为一段解释。

模型只负责组织语言，数值必须来自 data_context，知识必须来自 knowledge context。
没有模型或模型不可用时，退回「数据回答 + 知识要点」的确定性组合。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from ..services import llm_client
from .knowledge_agent import KnowledgeResult

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是「食物营养百科」的营养分析助手。请遵守以下规则：
1. 营养数值只能使用「营养数据」中的内容；数据里没有的项目直接说明未收录，禁止估算或编造。
2. 营养作用与解释只能使用「知识库依据」中的内容；没有依据时明确说知识库未覆盖。
3. 回答使用简体中文，先给结论，再给数据或解释；数值统一按每 100g 可食部分表述。
4. 不要给出疾病诊断、用药或个体化医疗建议；涉及此类问题提醒咨询医生或注册营养师。
5. 不要使用 Markdown 表格或加粗，前端按纯文本换行展示。
6. 如果使用了知识库依据，请在回答末尾用「来源：标题（机构）」列出，不要编造来源。

营养数据：
{data_context}

知识库依据：
{knowledge_context}
"""


@dataclass(frozen=True)
class AnalysisResult:
    reply: str
    mode: str


class NutritionAnalysisAgent:
    def compose(
        self,
        *,
        message: str,
        history: list[dict[str, str]],
        data_answer: str,
        data_context: str,
        knowledge: KnowledgeResult,
    ) -> AnalysisResult:
        if data_answer or knowledge.has_evidence:
            reply = llm_client.complete(
                system_prompt=SYSTEM_PROMPT.format(
                    data_context=data_context or "（本轮没有结构化营养数据）",
                    knowledge_context=knowledge.context or "（本轮没有检索到知识库依据）",
                ),
                user_message=message,
                history=history,
            )
            if reply:
                return AnalysisResult(reply=reply, mode="llm")

        return AnalysisResult(
            reply=self.fallback(data_answer, knowledge),
            mode="database" if data_answer else "rag",
        )

    def fallback(self, data_answer: str, knowledge: KnowledgeResult) -> str:
        if data_answer and knowledge.has_evidence:
            return f"{data_answer}\n\n{_knowledge_appendix(knowledge)}"
        if data_answer:
            return data_answer
        if knowledge.has_evidence:
            return knowledge.fallback_answer()
        return (
            "目前没有查到可以支撑这个问题的营养数据或知识库依据。\n"
            "可以补充具体的食物名称、营养素名称，或换一种问法后再试。"
        )


def _knowledge_appendix(knowledge: KnowledgeResult) -> str:
    lines = ["相关知识："]
    for citation in knowledge.citations[:3]:
        lines.append(f"· {citation.title}（{citation.source}）：{citation.snippet}")
    lines.append("以上知识内容来自检索到的知识库文档，未做超出原文的推断。")
    return "\n".join(lines)