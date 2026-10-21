#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Agent 工具（预留）。

工具是 AI 唯一被允许访问数据的方式，好处是：
1. 可以独立单元测试，不依赖模型；
2. 只读查询在这里约束，模型无法构造任意 SQL；
3. 返回结构化数据 + 简短文字摘要，便于模型引用与前端展示。

计划中的工具：
    search_foods(keyword, category, limit)      → 食物列表
    get_food_detail(food_id)                    → 营养明细 + 营养亮点
    compare_foods(food_ids, nutrient_code)      → 指定营养素对比
"""