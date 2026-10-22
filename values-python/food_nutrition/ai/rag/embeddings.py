#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""文本向量化。

默认使用本地哈希向量（hash-ngram），不依赖外部服务，方便离线开发与测试；
配置 EMBEDDING_PROVIDER=openai 后改用 OpenAI 兼容的 /embeddings 接口。

无论哪种实现，维度都由 EMBEDDING_DIM 统一控制；换模型后必须重建向量索引，
否则 Qdrant collection 的维度会与查询向量不一致。
"""

from __future__ import annotations

import hashlib
import logging
import math
import os
import re
from typing import Protocol

import requests

from ..settings import RagSettings, load_rag

logger = logging.getLogger(__name__)

_ASCII_WORD = re.compile(r"[a-z0-9]+")
_CHINESE_RUN = re.compile(r"[\u4e00-\u9fff]+")


class EmbeddingModel(Protocol):
    dimension: int
    name: str

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        ...


class HashingEmbedding:
    """基于字符 n-gram 的确定性哈希向量。

    它不是语义模型，但对「蛋白质有什么作用」这类关键词明确的中文问题足够稳定：
    中文按单字 + 二元组、英文按单词切分，再哈希到固定维度并做 L2 归一化。
    优点是完全离线、结果可复现，适合作为默认降级方案。
    """

    def __init__(self, dimension: int = 384, name: str = "hash-ngram-v1") -> None:
        self.dimension = dimension
        self.name = name

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        for token in _tokenize(text):
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            bucket = int.from_bytes(digest[:4], "big") % self.dimension
            sign = 1.0 if digest[4] & 1 else -1.0
            vector[bucket] += sign

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]


class OpenAIEmbedding:
    """OpenAI 兼容 /embeddings 接口。"""

    def __init__(
        self,
        *,
        dimension: int,
        model: str,
        base_url: str,
        api_key: str,
        timeout: tuple[float, float] = (3.0, 30.0),
    ) -> None:
        self.dimension = dimension
        self.name = model
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), 32):
            batch = texts[start : start + 32]
            response = requests.post(
                f"{self._base_url}/embeddings",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={"model": self._model, "input": batch},
                timeout=self._timeout,
            )
            response.raise_for_status()
            payload = response.json().get("data", [])
            payload.sort(key=lambda item: item.get("index", 0))
            for item in payload:
                vector = item.get("embedding") or []
                if len(vector) != self.dimension:
                    raise ValueError(
                        f"嵌入维度不一致：配置 {self.dimension}，接口返回 {len(vector)}"
                    )
                vectors.append([float(value) for value in vector])
        return vectors


def create_embedding(settings: RagSettings | None = None) -> EmbeddingModel:
    settings = settings or load_rag()
    if settings.embedding_provider != "openai":
        return HashingEmbedding(settings.embedding_dim, settings.embedding_model)

    api_key = os.getenv(settings.embedding_api_key_env)
    if not api_key:
        logger.warning(
            "EMBEDDING_PROVIDER=openai 但 %s 未设置，降级为本地哈希向量",
            settings.embedding_api_key_env,
        )
        return HashingEmbedding(settings.embedding_dim, "hash-ngram-fallback")
    return OpenAIEmbedding(
        dimension=settings.embedding_dim,
        model=settings.embedding_model,
        base_url=settings.embedding_base_url,
        api_key=api_key,
    )


def _tokenize(text: str) -> list[str]:
    normalized = (text or "").lower()
    tokens: list[str] = _ASCII_WORD.findall(normalized)

    for run in _CHINESE_RUN.findall(normalized):
        # 只用二元组，不用单字：单字会让「的 / 有 / 用」这类高频字把所有文档都拉高，
        # 短到只有一个字时再退回单字，避免完全丢词。
        if len(run) == 1:
            tokens.append(run)
        else:
            tokens.extend(run[index : index + 2] for index in range(len(run) - 1))

    return tokens