#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""答案审核。

重点不是润色，而是拦住两类问题：
1. 模型回答里出现了营养上下文没有的数值（最常见的幻觉）；
2. 回答声称有依据，但引用列表为空。

确定性数据库回答由代码生成，不重复做数值审核。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..rag.retriever import Citation

_NUMBER_UNIT = re.compile(
    r"(\d+(?:\.\d+)?)\s*(kcal|千卡|g|克|mg|毫克|µg|微克|%|NRV)",
    re.IGNORECASE,
)

_UNIT_FAMILY = {
    "kcal": "kcal",
    "千卡": "kcal",
    "g": "g",
    "克": "g",
    "mg": "mg",
    "毫克": "mg",
    "µg": "µg",
    "微克": "µg",
    "%": "%",
    "nrv": "%",
}


@dataclass(frozen=True)
class ReviewResult:
    approved: bool
    issues: list[str] = field(default_factory=list)


class AnswerReviewer:
    def review(
        self,
        *,
        reply: str,
        mode: str,
        data_context: str,
        citations: list[Citation],
    ) -> ReviewResult:
        if mode != "llm":
            return ReviewResult(approved=True)

        issues: list[str] = []
        if not citations:
            issues.append("回答没有携带任何引用")

        allowed = _numeric_tokens(data_context)
        for token in _numeric_tokens(reply):
            if token not in allowed:
                issues.append(f"回答中的数值 {token[0]}{token[1]} 不在营养数据上下文中")

        if "尚未接入" in reply:
            issues.append("模型回答包含占位文案")

        return ReviewResult(approved=not issues, issues=issues)


def _numeric_tokens(text: str) -> set[tuple[float, str]]:
    tokens: set[tuple[float, str]] = set()
    for raw_value, raw_unit in _NUMBER_UNIT.findall(text or ""):
        unit = _UNIT_FAMILY.get(raw_unit.lower())
        if unit is None:
            continue
        tokens.add((round(float(raw_value), 3), unit))
    return tokens