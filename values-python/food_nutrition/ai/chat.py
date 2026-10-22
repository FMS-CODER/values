#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""营养问答生成。

两条路径：
1. 配置了模型 API Key：把检索到的营养库数据作为上下文交给 OpenAI 兼容接口，
   回答里只允许复述上下文中的数值；接口失败时退回路径 2。
2. 没有 Key 或模型不可用：直接用营养库数据拼出确定性回答（mode=database）。

两条路径都遵守同一约束：库中没有的数据就说「没有」，不补一个看起来合理的数字。
"""

from __future__ import annotations

import logging
from typing import Any

import requests

from . import retrieval
from .settings import load

logger = logging.getLogger(__name__)

# 与 Java 占位实现保持同一组引导问题，前端目前不消费 suggestions，保留是为了接口稳定
SUGGESTIONS = [
    "西兰花有哪些营养亮点？",
    "高蛋白的食物有哪些？",
    "苹果的维生素 C 算高吗？",
]

ADVICE_WORDS = ("建议", "减脂", "减肥", "儿童", "孕妇", "糖尿病", "高血压", "怎么吃", "搭配")

SYSTEM_PROMPT = """你是「食物营养百科」的营养问答助手。请遵守以下规则：
1. 只能使用下方「营养库数据」中的数值回答；数据里没有的内容直接说明未收录，禁止编造或估算数值。
2. 回答使用简体中文，简洁、口语化，先给结论再列数据；数值统一按每 100g 可食部分表述。
3. 不要给出疾病诊断、用药或个体化医疗建议；涉及此类问题提醒咨询医生或注册营养师。
4. 不要使用 Markdown 表格或加粗，前端按纯文本换行展示。

营养库数据：
{context}
"""


def answer(message: str, history: list[dict[str, str]] | None = None) -> tuple[str, str, list[str]]:
    """返回 (reply, mode, suggestions)。"""
    foods = retrieval.find_foods(message)
    nutrient = retrieval.detect_nutrient(message)
    category = retrieval.detect_category(message)
    low_intent = retrieval.is_low_intent(message)

    llm_reply = _ask_llm(message, history or [], foods, nutrient, category)
    if llm_reply:
        return llm_reply, "llm", SUGGESTIONS

    reply = _database_answer(message, foods, nutrient, category, low_intent)
    return reply, "database", SUGGESTIONS


# ------------------------------------------------------------------ 数据库回答


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
    macros = [
        nutrients[code]
        for code in retrieval.MACRO_CODES
        if code in nutrients
    ]

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

    rows = retrieval.top_foods(
        code,
        limit=5,
        category_code=category,
        ascending=low_intent,
    )
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
    for food, rows in ((first, first_rows), (second, second_rows)):
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


# ------------------------------------------------------------------ 模型回答

DEFAULT_BASE_URLS = {
    "openai": "https://api.openai.com/v1",
    "deepseek": "https://api.deepseek.com/v1",
    "dashscope": "https://dashscope.aliyuncs.com/compatible-mode/v1",
}


def _ask_llm(
    message: str,
    history: list[dict[str, str]],
    foods: list[dict[str, Any]],
    nutrient: str | None,
    category: str | None,
) -> str | None:
    """调用模型；未配置 Key、请求失败或返回为空时返回 None，由调用方降级。"""
    settings = load()
    api_key = settings.api_key()
    if not api_key:
        return None

    context = _build_context(foods, nutrient, category)
    messages: list[dict[str, str]] = [
        {"role": "system", "content": SYSTEM_PROMPT.format(context=context)}
    ]
    for item in history[-8:]:
        role = item.get("role")
        content = (item.get("content") or "").strip()
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": message})

    base_url = settings.base_url or DEFAULT_BASE_URLS.get(
        settings.provider, DEFAULT_BASE_URLS["openai"]
    ).rstrip("/")

    try:
        response = requests.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.model,
                "temperature": settings.temperature,
                "messages": messages,
            },
            timeout=(3, 30),
        )
        response.raise_for_status()
        payload = response.json()
        content = payload["choices"][0]["message"]["content"]
        if isinstance(content, str) and content.strip():
            return content.strip()
        logger.warning("模型返回了空内容，降级为营养库回答")
    except Exception as exc:  # 供应商差异大，这里统一降级而不是把异常抛给前端
        logger.warning("调用模型失败，降级为营养库回答：%s", exc)
    return None


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