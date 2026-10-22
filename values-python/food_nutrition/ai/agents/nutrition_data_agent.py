#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""营养数据 Agent。

只做确定性工作：实体识别、SQL 查询、数值格式化。
不调用大模型，也不生成没有入库依据的数值。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .. import retrieval
from ..rag.retriever import Citation

ADVICE_WORDS = ("建议", "减脂", "减肥", "儿童", "孕妇", "糖尿病", "高血压", "怎么吃", "搭配")


@dataclass
class DataResult:
    answer: str
    context: str
    citations: list[Citation] = field(default_factory=list)
    foods: list[dict[str, Any]] = field(default_factory=list)
    nutrient: str | None = None
    category: str | None = None
    low_intent: bool = False


class NutritionDataAgent:
    def inspect(self, message: str) -> DataResult:
        foods = retrieval.find_foods(message)
        nutrient = retrieval.detect_nutrient(message)
        category = retrieval.detect_category(message)
        low_intent = retrieval.is_low_intent(message)

        return DataResult(
            answer=_database_answer(message, foods, nutrient, category, low_intent),
            context=_build_context(foods, nutrient, category),
            citations=_citations(foods, nutrient, category),
            foods=foods,
            nutrient=nutrient,
            category=category,
            low_intent=low_intent,
        )


def _database_answer(
    message: str,
    foods: list[dict[str, Any]],
    nutrient: str | None,
    category: str | None,
    low_intent: bool,
) -> str:
    if len(foods) >= 2:
        return _compare_foods(foods[0], foods[1])

    if foods:
        food = foods[0]
        if nutrient:
            return _explain_food_nutrient(food, nutrient)
        return _describe_food(food)

    if nutrient:
        return _rank_foods(nutrient, category, low_intent)

    return _generic_answer(message)


def _describe_food(food: dict[str, Any]) -> str:
    nutrients = {row["code"]: row for row in retrieval.food_nutrients(food["id"])}
    macros = [nutrients[code] for code in retrieval.MACRO_CODES if code in nutrients]

    lines = [f"{food['name']}（{food['category_name']}，每 100g 可食部分）"]
    description = (food.get("description") or "").strip()
    if description:
        lines.append(description)

    if macros:
        macro_text = " · ".join(
            f"{row['name']} {retrieval.format_amount(row['amount'])} {row['unit']}"
            for row in macros
        )
        lines.extend(["", macro_text])

    highlights = retrieval.food_highlights(food["id"])
    if highlights:
        lines.extend(["", "营养亮点："])
        for row in highlights[:4]:
            amount = retrieval.format_amount(row["amount"])
            percent = retrieval.format_percent(row.get("nrv_percent"))
            suffix = f"，约 {percent} NRV" if percent else ""
            lines.append(f"· {row['nutrient_name']}：{amount} {row['unit']}{suffix}")
    else:
        lines.extend(["", "按当前富含判定规则，这款食物没有营养素达到「富含」标准。"])

    lines.extend(["", "以上数值来自食物营养库，烹饪方式会改变实际摄入量。"])
    return "\n".join(lines)


def _explain_food_nutrient(food: dict[str, Any], code: str) -> str:
    rule = retrieval.nutrient_rule(code)
    if rule is None:
        return "食物营养库中没有这个营养素的信息。"

    rows = {row["code"]: row for row in retrieval.food_nutrients(food["id"])}
    row = rows.get(code)
    nutrient_name = rule["name"]

    if row is None:
        return (
            f"食物营养库中没有「{food['name']}」的{nutrient_name}数据，"
            "因此不能据此判断它的含量高低。"
        )

    amount = retrieval.format_amount(row["amount"])
    percent = retrieval.format_percent(row.get("nrv_percent"))
    lines = [f"{food['name']}每 100g 含{nutrient_name} {amount} {rule['unit']}。"]
    if percent:
        lines.append(f"按 NRV 折算约 {percent}。")
    else:
        lines.append("该营养素没有 NRV 参考值，无法折算百分比。")

    rule_text = _rule_text(rule)
    if rule_text:
        lines.append(f"当前富含判定规则为「{rule_text}」。")
        threshold_hit = any(
            item["nutrient_code"] == code for item in retrieval.food_highlights(food["id"])
        )
        if threshold_hit:
            lines.append(f"这款食物已达到{nutrient_name}的富含标准。")
        else:
            lines.append(f"这款食物未达到{nutrient_name}的富含标准，但含量仍需结合食用量看。")
    else:
        lines.append("该营养素暂未配置富含判定规则，只能提供含量与 NRV 百分比。")

    lines.append("以上均按每 100g 可食部分计。")
    return "\n".join(lines)


def _rank_foods(code: str, category: str | None, low_intent: bool) -> str:
    rule = retrieval.nutrient_rule(code)
    if rule is None:
        return "食物营养库中没有这个营养素的信息。"

    rows = retrieval.top_foods(code, limit=5, category_code=category, ascending=low_intent)
    nutrient_name = rule["name"]
    category_name = _category_name(category)
    scope = category_name or "食物"

    title = (
        f"{scope}中{nutrient_name}含量较低的（每 100g）"
        if low_intent
        else f"{scope}中{nutrient_name}含量较高的（每 100g）"
    )
    if not rows:
        return f"食物营养库中没有找到{scope}的{nutrient_name}数据。"

    lines = [title]
    for index, row in enumerate(rows, start=1):
        amount = retrieval.format_amount(row["amount"])
        percent = retrieval.format_percent(row.get("nrv_percent"))
        suffix = f"，约 {percent} NRV" if percent else ""
        lines.append(
            f"{index}. {row['name']}（{row['category_name']}）：{amount} {rule['unit']}{suffix}"
        )

    lines.extend(
        [
            "",
            "排名只比较食物营养库中已录入的数据，不代表所有同类食物。",
            "数值按每 100g 可食部分计。",
        ]
    )
    return "\n".join(lines)


def _compare_foods(first: dict[str, Any], second: dict[str, Any]) -> str:
    first_rows = {row["code"]: row for row in retrieval.food_nutrients(first["id"])}
    second_rows = {row["code"]: row for row in retrieval.food_nutrients(second["id"])}

    lines = [f"{first['name']} 与 {second['name']} 的营养对比（每 100g 可食部分）"]
    for code in retrieval.MACRO_CODES:
        left = first_rows.get(code)
        right = second_rows.get(code)
        if left is None and right is None:
            continue
        name = (left or right)["name"]
        unit = (left or right)["unit"]
        left_text = retrieval.format_amount(left["amount"]) if left else "未收录"
        right_text = retrieval.format_amount(right["amount"]) if right else "未收录"
        lines.append(f"· {name}：{left_text} {unit} / {right_text} {unit}")

    lines.extend(["", "营养亮点："])
    for food in (first, second):
        highlights = retrieval.food_highlights(food["id"])
        names = "、".join(item["nutrient_name"] for item in highlights[:3])
        lines.append(f"· {food['name']}：{names or '暂无达到富含标准的营养素'}")

    lines.extend(["", "两项数值均来自食物营养库，未收录的项目不作推测。"])
    return "\n".join(lines)


def _generic_answer(message: str) -> str:
    lines = [
        "我可以基于食物营养库回答这些问题：",
        "· 某种食物的营养构成与亮点，例如「西兰花有哪些营养亮点？」",
        "· 某类营养素含量较高或较低的食物，例如「哪些食物蛋白质含量较高？」",
        "· 两种食物的营养对比，例如「鸡胸肉和牛里脊有什么区别？」",
        "",
        "当前问题没有定位到具体的食物或营养素，补充食物名称或营养素名称后我再查库回答。",
    ]

    if any(word in message for word in ADVICE_WORDS):
        lines.extend(
            [
                "",
                "饮食搭配和疾病相关的个体化建议需要医生或注册营养师判断，"
                "我只能提供营养库中记录的食物成分数值。",
            ]
        )
    return "\n".join(lines)


def _build_context(
    foods: list[dict[str, Any]],
    nutrient: str | None,
    category: str | None,
) -> str:
    lines: list[str] = []

    counts = retrieval.category_counts()
    total = sum(int(item["food_count"]) for item in counts)
    category_text = "、".join(f"{item['name']}({item['food_count']})" for item in counts)
    lines.append(f"食物库共 {total} 条食物；分类与数量：{category_text}。")

    for food in foods[:2]:
        lines.append(f"\n食物：{food['name']}（{food['category_name']}）")
        description = (food.get("description") or "").strip()
        if description:
            lines.append(f"简介：{description}")

        nutrients = retrieval.food_nutrients(food["id"])
        if nutrients:
            text = "，".join(
                f"{row['name']} {retrieval.format_amount(row['amount'])} {row['unit']}"
                for row in nutrients
            )
            lines.append(f"每 100g 营养成分：{text}")

        highlights = retrieval.food_highlights(food["id"])
        if highlights:
            text = "，".join(
                f"{row['nutrient_name']} {retrieval.format_amount(row['amount'])} {row['unit']}"
                f"（{retrieval.format_percent(row.get('nrv_percent')) or '无 NRV'}）"
                for row in highlights[:6]
            )
            lines.append(f"达到富含标准的营养素：{text}")

    if nutrient:
        rule = retrieval.nutrient_rule(nutrient)
        if rule:
            rows = retrieval.top_foods(nutrient, limit=8)
            text = "，".join(
                f"{row['name']} {retrieval.format_amount(row['amount'])} {rule['unit']}"
                for row in rows
            )
            lines.append(f"\n{rule['name']}含量靠前的食物（每 100g）：{text or '无数据'}")

    if category:
        name = _category_name(category)
        if name:
            lines.append(f"\n用户提到的食物分类：{name}；生成排名时只应使用该分类的数据。")

    return "\n".join(lines)


def _citations(
    foods: list[dict[str, Any]],
    nutrient: str | None,
    category: str | None,
) -> list[Citation]:
    citations: list[Citation] = []
    for food in foods[:2]:
        citations.append(_food_citation(food))

    if nutrient and not foods:
        rule = retrieval.nutrient_rule(nutrient)
        if rule:
            rows = retrieval.top_foods(nutrient, limit=5, category_code=category)
            snippet = "；".join(
                f"{row['name']} {retrieval.format_amount(row['amount'])} {rule['unit']}"
                for row in rows
            )
            citations.append(
                Citation(
                    document_id=f"nutrient-ranking:{nutrient}:{category or 'ALL'}",
                    title=f"{rule['name']}含量排名",
                    source="食物营养库",
                    url="",
                    snippet=snippet or "库中暂无相关排名数据",
                    score=1.0,
                    kind="food",
                    review_status="approved",
                    version="1",
                )
            )
    return citations


def _food_citation(food: dict[str, Any]) -> Citation:
    nutrients = {row["code"]: row for row in retrieval.food_nutrients(food["id"])}
    snippet = "；".join(
        f"{nutrients[code]['name']} {retrieval.format_amount(nutrients[code]['amount'])}"
        f" {nutrients[code]['unit']}"
        for code in retrieval.MACRO_CODES
        if code in nutrients
    )
    return Citation(
        document_id=f"food:{food['id']}",
        title=f"{food['name']}的营养成分",
        source=(food.get("source_name") or food.get("source_note") or "食物营养库"),
        url="",
        snippet=snippet or "每 100g 可食部分",
        score=1.0,
        kind="food",
        review_status="approved" if food.get("verified") else "pending",
        version="1",
    )


def _rule_text(rule: dict[str, Any]) -> str | None:
    rule_type = rule.get("rich_rule_type")
    if rule_type == "NRV_PERCENT" and rule.get("rich_threshold_percent") is not None:
        return f"≥{retrieval.format_amount(rule['rich_threshold_percent'])}% NRV 为富含"
    if rule_type == "ABSOLUTE" and rule.get("rich_threshold_per_100g") is not None:
        return (
            f"≥{retrieval.format_amount(rule['rich_threshold_per_100g'])}"
            f"{rule['unit']}/100g 为富含"
        )
    return None


def _category_name(code: str | None) -> str | None:
    if not code:
        return None
    for item in retrieval.category_counts():
        if item["code"] == code:
            return item["name"]
    return None