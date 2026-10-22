#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI 层配置。

只做「读环境变量 + 给出默认值」，不 import langchain：
本文件要在未安装 AI 依赖的环境里也能被安全导入（例如被诊断脚本读取配置）。

凭据一律来自环境变量，参见仓库根 .env.example。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from ..config import REPO_ROOT


@dataclass(frozen=True)
class LlmSettings:
    """模型连接参数。字段名保持通用，换供应商时只改这里。"""

    provider: str
    model: str
    temperature: float
    api_key_env: str
    base_url: str | None

    def api_key(self) -> str | None:
        return os.getenv(self.api_key_env)


def load() -> LlmSettings:
    """按当前环境变量组装配置；未设置 API Key 时返回的配置仍然可用（仅缺凭据）。"""
    provider = os.getenv("AI_PROVIDER", "openai").lower()

    # 默认值与供应商解耦：换模型只改环境变量，不动代码
    defaults = {
        "openai": ("gpt-4o-mini", "OPENAI_API_KEY"),
        "deepseek": ("deepseek-chat", "DEEPSEEK_API_KEY"),
        "dashscope": ("qwen-plus", "DASHSCOPE_API_KEY"),
    }
    model_default, key_env = defaults.get(provider, defaults["openai"])

    return LlmSettings(
        provider=provider,
        model=os.getenv("AI_MODEL", model_default),
        temperature=float(os.getenv("AI_TEMPERATURE", "0.2")),
        api_key_env=os.getenv("AI_API_KEY_ENV", key_env),
        base_url=os.getenv("AI_BASE_URL") or None,
    )


@dataclass(frozen=True)
class RagSettings:
    """RAG 与向量库配置。

    embedding_dim 必须与 Qdrant collection 的向量维度一致；切换 embedding 模型后
    需要执行一次 `python -m food_nutrition rag-index --rebuild` 重建索引。
    """

    qdrant_enabled: bool
    qdrant_url: str
    qdrant_api_key: str | None
    collection: str
    embedding_provider: str
    embedding_model: str
    embedding_dim: int
    embedding_base_url: str
    embedding_api_key_env: str
    top_k: int
    min_score: float
    auto_index: bool
    knowledge_dir: Path
    include_pending: bool


def load_rag() -> RagSettings:
    provider = os.getenv("EMBEDDING_PROVIDER", "hash").lower()
    # hash 是离线可用的确定性向量，不依赖外部服务；openai 走兼容 /embeddings 接口
    default_dim = 1536 if provider == "openai" else 384
    default_base = (
        "https://api.openai.com/v1" if provider == "openai" else ""
    )

    return RagSettings(
        qdrant_enabled=os.getenv("QDRANT_ENABLED", "true").lower() not in ("0", "false", "no"),
        qdrant_url=os.getenv("QDRANT_URL", "http://127.0.0.1:6333"),
        qdrant_api_key=os.getenv("QDRANT_API_KEY") or None,
        collection=os.getenv("QDRANT_COLLECTION", "nutrition_knowledge"),
        embedding_provider=provider,
        embedding_model=os.getenv(
            "EMBEDDING_MODEL",
            "text-embedding-3-small" if provider == "openai" else "hash-ngram-v1",
        ),
        embedding_dim=int(os.getenv("EMBEDDING_DIM", str(default_dim))),
        embedding_base_url=os.getenv("EMBEDDING_BASE_URL", default_base).rstrip("/"),
        embedding_api_key_env=os.getenv("EMBEDDING_API_KEY_ENV", "OPENAI_API_KEY"),
        top_k=int(os.getenv("RAG_TOP_K", "4")),
        min_score=float(os.getenv("RAG_MIN_SCORE", "0.2")),
        auto_index=os.getenv("RAG_AUTO_INDEX", "true").lower() not in ("0", "false", "no"),
        knowledge_dir=Path(
            os.getenv("KNOWLEDGE_DIR", str(REPO_ROOT / "values-python" / "data" / "knowledge"))
        ),
        include_pending=os.getenv("RAG_INCLUDE_PENDING", "false").lower() in ("1", "true", "yes"),
    )