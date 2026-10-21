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