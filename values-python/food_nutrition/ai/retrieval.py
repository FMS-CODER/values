#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""营养库检索。

AI 回答只使用这里从数据库读出的数值：
- 不在这里硬编码任何营养数据，避免与 food_nutrient 表出现两份口径；
- 生成回答时也只用这些查询结果，模型拿不到数据时明确说明「库中没有」，
  而不是编一个看起来合理的数字。

对上层（chat.py / server.py）暴露的查询都是同步的：数据量只有百余条食物，
单次请求内直连查询足够快，先不引入连接池与异步驱动。
"""

from __future__ import annotations

from typing import Any

from ..db import connect

# 关键词按长度从长到短匹配，避免「维生素 C」被更短的「维生素」抢先命中。
# 值统一用 nutrient_info.code，与数据库保持一致。
NUTRIENT_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("SATURATED_FAT", ("饱和脂肪", "饱和脂肪酸")),
    ("CHOLESTEROL", ("胆固醇",)),
    ("VITAMIN_B12", ("维生素b12", "维生素 b12", "b12")),
    ("VITAMIN_C", ("维生素c", "维生素 c", "维c", "vc")),
    ("VITAMIN_A", ("维生素a", "维生素 a", "维a", "β-胡萝卜素", "β胡萝卜素", "胡萝卜素")),
    ("VITAMIN_D", ("维生素d", "维生素 d", "维d")),
    ("VITAMIN_E", ("维生素e", "维生素 e", "维e")),
    ("VITAMIN_K", ("维生素k", "维生素 k", "维k")),
    ("CARBOHYDRATE", ("碳水化合物", "碳水")),
    ("PROTEIN", ("蛋白质", "蛋白")),
    ("FIBER", ("膳食纤维", "纤维")),
    ("ENERGY", ("热量", "卡路里", "千卡", "能量")),
    ("FOLATE", ("叶酸",)),
    ("CALCIUM", ("钙",)),
    ("POTASSIUM", ("钾",)),
    ("MAGNESIUM", ("镁",)),
    ("PHOSPHORUS", ("磷",)),
    ("SELENIUM", ("硒",)),
    ("SODIUM", ("钠",)),
    ("IRON", ("铁",)),
    ("ZINC", ("锌",)),
    ("SUGAR", ("含糖量", "糖分", "糖")),
    ("FAT", ("脂肪",)),
)

# 分类词用于把「低糖水果」这类问题收窄到某个分类，避免把蔬菜算进水果排名
CATEGORY_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("VEGETABLE", ("蔬菜", "青菜")),
    ("FRUIT", ("水果",)),
    ("GRAIN", ("谷物", "主食", "杂粮")),
    ("LEGUME", ("豆类", "豆制品")),
    ("NUT_SEED", ("坚果", "种子")),
    ("EGG", ("蛋类", "鸡蛋")),
    ("DAIRY", ("奶制品", "乳制品", "牛奶")),
    ("FISH", ("鱼类", "海鲜")),
    ("MEAT", ("肉类", "红肉")),
    ("POULTRY", ("禽类", "鸡肉")),
    ("OIL_FAT", ("油脂", "食用油")),
    ("BEVERAGE", ("饮料", "果汁")),
)

# 判断「低 / 少」方向的问题；只影响排序方向，不改变数值本身
LOW_INTENT_WORDS = ("低", "少", "减", "控制", "避免", "不含")

MACRO_CODES = ("ENERGY", "PROTEIN", "FAT", "CARBOHYDRATE", "FIBER", "SUGAR")


def _fetch_all(sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    """执行只读查询。连接用完即关，避免 Web 请求线程长期占用连接。"""
    connection = connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchall()
    finally:
        connection.close()


def list_foods() -> list[dict[str, Any]]:
    """全部食物。百余条数据整表取回，再在内存里做名称匹配，避免拼 LIKE 造成误命中。"""
    return _fetch_all(
        """
        SELECT f.id,
               f.name,
               f.name_en,
               f.description,
               fc.code AS category_code,
               fc.name AS category_name
        FROM food f
        JOIN food_category fc ON fc.id = f.category_id
        ORDER BY f.id
        """
    )


def find_foods(message: str, limit: int = 3) -> list[dict[str, Any]]:
    """从问题中找出被提到的食物。

    先按中文名匹配，再按英文名兜底；如果一个短名称是另一个已命中名称的一部分
    （例如「鸡胸肉」与「熟鸡胸肉」），只保留更长的那个，避免同一句话命中两条。
    """
    normalized = message.lower()
    matched: list[dict[str, Any]] = []

    for food in list_foods():
        name = (food.get("name") or "").strip()
        name_en = (food.get("name_en") or "").strip()

        if name and name in message:
            matched.append(food)
        elif len(name_en) >= 4 and name_en.lower() in normalized:
            matched.append(food)

    matched.sort(key=lambda item: len(item.get("name") or ""), reverse=True)

    result: list[dict[str, Any]] = []
    for food in matched:
        name = food.get("name") or ""
        if any(name != other.get("name") and name in (other.get("name") or "") for other in result):
            continue
        result.append(food)
        if len(result) >= limit:
            break
    return result


def detect_nutrient(message: str) -> str | None:
    """识别问题里提到的营养素编码。"""
    normalized = message.lower()
    for code, keywords in NUTRIENT_KEYWORDS:
        if any(keyword in normalized for keyword in keywords):
            return code
    return None


def detect_category(message: str) -> str | None:
    """识别问题里提到的食物分类编码。"""
    for code, keywords in CATEGORY_KEYWORDS:
        if any(keyword in message for keyword in keywords):
            return code
    return None


def is_low_intent(message: str) -> bool:
    """「低糖」「少油」这类问题需要升序排序。"""
    return any(word in message for word in LOW_INTENT_WORDS)


def food_nutrients(food_id: int) -> list[dict[str, Any]]:
    """单条食物的全部已入库营养素，含按 NRV 换算的百分比。"""
    return _fetch_all(
        """
        SELECT ni.code,
               ni.name,
               ni.unit,
               ni.nutrient_group,
               ni.sort_order,
               fn.amount,
               CASE
                 WHEN ni.nrv_value IS NULL THEN NULL
                 ELSE ROUND(fn.amount * COALESCE(ni.nrv_conversion_factor, 1) / ni.nrv_value * 100, 1)
               END AS nrv_percent
        FROM food_nutrient fn
        JOIN nutrient_info ni ON ni.code = fn.nutrient_code
        WHERE fn.food_id = %s AND fn.basis_type = '100G'
        ORDER BY ni.nutrient_group, ni.sort_order
        """,
        (food_id,),
    )


def food_highlights(food_id: int) -> list[dict[str, Any]]:
    """达到「富含」判定且配好科普说明的营养素，按 NRV% 从高到低。"""
    return _fetch_all(
        """
        SELECT nutrient_code,
               nutrient_name,
               unit,
               amount,
               nrv_percent,
               rule_note,
               role
        FROM v_food_highlight
        WHERE food_id = %s
        ORDER BY COALESCE(nrv_percent, 0) DESC, sort_order
        """,
        (food_id,),
    )


def nutrient_rule(code: str) -> dict[str, Any] | None:
    """营养素名称、单位与富含判定规则。"""
    rows = _fetch_all(
        """
        SELECT code, name, unit, nrv_value, rich_rule_type,
               rich_threshold_percent, rich_threshold_per_100g, rule_note
        FROM nutrient_info
        WHERE code = %s
        """,
        (code,),
    )
    return rows[0] if rows else None


def top_foods(
    code: str,
    *,
    limit: int = 5,
    category_code: str | None = None,
    ascending: bool = False,
) -> list[dict[str, Any]]:
    """按某营养素含量排序的食物。

    排序方向与分类都来自代码内的枚举判断，不拼接用户输入，避免 SQL 注入。
    """
    direction = "ASC" if ascending else "DESC"
    where = ["fn.nutrient_code = %s", "fn.basis_type = '100G'"]
    params: list[Any] = [code]

    if category_code:
        where.append("fc.code = %s")
        params.append(category_code)

    # 零值通常代表「未检出 / 未导入」，参与「含量高」排名没有意义；
    # 但「低糖」这类升序问题需要保留 0，否则会把真正低糖的食物排除掉。
    if not ascending:
        where.append("fn.amount > 0")

    sql = f"""
        SELECT f.id,
               f.name,
               fc.name AS category_name,
               fn.amount,
               ni.name AS nutrient_name,
               ni.unit,
               CASE
                 WHEN ni.nrv_value IS NULL THEN NULL
                 ELSE ROUND(fn.amount * COALESCE(ni.nrv_conversion_factor, 1) / ni.nrv_value * 100, 1)
               END AS nrv_percent
        FROM food_nutrient fn
        JOIN food f ON f.id = fn.food_id
        JOIN food_category fc ON fc.id = f.category_id
        JOIN nutrient_info ni ON ni.code = fn.nutrient_code
        WHERE {' AND '.join(where)}
        ORDER BY fn.amount {direction}, f.id
        LIMIT %s
    """
    params.append(limit)

    return _fetch_all(sql, tuple(params))


def category_counts() -> list[dict[str, Any]]:
    """分类与食物数量，供通用问题给出可查询的范围。"""
    return _fetch_all(
        """
        SELECT fc.code, fc.name, COUNT(f.id) AS food_count
        FROM food_category fc
        LEFT JOIN food f ON f.category_id = fc.id
        GROUP BY fc.id, fc.code, fc.name, fc.sort_order
        ORDER BY fc.sort_order
        """
    )


def format_amount(value: Any) -> str:
    """把 Decimal 转成适合阅读的字符串，最多保留两位小数。"""
    if value is None:
        return "-"
    text = f"{float(value):.2f}".rstrip("0").rstrip(".")
    return text or "0"


def format_percent(value: Any) -> str | None:
    if value is None:
        return None
    return f"{format_amount(value)}%"