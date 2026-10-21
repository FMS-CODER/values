#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全局配置：路径、数据库与外部服务凭据。

为什么集中在这里：
1. 脚本拆成多个模块后，各自推算「项目根在哪」会随目录调整集体失效，
   统一以本文件位置为锚点向上推导，移动整个 values-python 目录也不会出错；
2. 数据库口令、第三方 API Key 一律环境变量优先，避免把真实凭据写进代码；
3. 后续 AI 层（LangChain / LangGraph）要复用同一套数据库与数据目录，不应另写一份。

目录约定：
    values/                        仓库根
    ├── values-python/             本服务（Python 侧）
    │   ├── food_nutrition/        代码包
    │   └── data/images/           运行产物（清单、审核结果），不放代码
    └── values-front/public/foods/ 前端静态图片
"""

from __future__ import annotations

import os
from pathlib import Path

# config.py 位于 values-python/food_nutrition/，据此推导上两级
PACKAGE_ROOT = Path(__file__).resolve().parent
PYTHON_ROOT = PACKAGE_ROOT.parent
REPO_ROOT = PYTHON_ROOT.parent

# 前端静态资源目录：数据库里的 image_url(/foods/x.jpg) 去掉前导斜杠后拼到这里
PUBLIC_DIR = REPO_ROOT / "values-front" / "public"
FOOD_IMAGE_DIR = PUBLIC_DIR / "foods"

# 运行产物与代码分离，便于 .gitignore 与备份策略区分对待
DATA_DIR = PYTHON_ROOT / "data" / "images"

# 各模块的配置（映射表）留在各自包内，随代码一起版本化
INGESTION_MAPPINGS_DIR = PACKAGE_ROOT / "ingestion" / "mappings"
IMAGE_MAPPINGS_DIR = PACKAGE_ROOT / "images" / "mappings"

IMAGE_MANIFEST = DATA_DIR / "food-image-manifest.csv"
REVIEW_NEEDED = DATA_DIR / "review-needed.csv"
REJECTED_CANDIDATES = DATA_DIR / "rejected-candidates.csv"

# USDA 原始数据体积大且不随仓库分发，用环境变量指向本机路径
DEFAULT_USDA_JSON = Path(
    os.getenv(
        "USDA_JSON_PATH",
        r"c:\Users\LEGION\Desktop\FoodData_Central_foundation_food_json_2026-04-30.json",
    )
)


def db_config() -> dict:
    """数据库连接参数。

    默认值只服务于本机原型；部署时用 DB_* 环境变量覆盖，口令不落代码库。
    """
    return {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "3306")),
        "user": os.getenv("DB_USER", "root"),
        "password": os.getenv("DB_PASSWORD", "123456"),
        "database": os.getenv("DB_NAME", "values"),
    }


def ensure_data_dir() -> None:
    """首次运行时创建产物目录，避免各脚本各自 mkdir 时漏掉某条分支。"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)