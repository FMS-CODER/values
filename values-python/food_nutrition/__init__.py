#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""食物营养百科的数据侧 Python 包。

分层：
    ingestion/  USDA 原始数据 → MySQL（一次性/可重跑的数据导入）
    images/     食物图片的搜索、下载、审核清单
    ai/         预留：LangChain / LangGraph 扩展位（当前只有骨架）

命令统一从 `python -m food_nutrition` 进入，见 cli.py。
"""

__version__ = "0.1.0"