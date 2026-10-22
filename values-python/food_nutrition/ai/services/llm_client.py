#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OpenAI 兼容聊天接口封装。

所有 Agent 共用这一份配置与降级逻辑：
- 没有 Key 时返回 None，由调用方走确定性回答；
- 请求失败或返回空内容时返回 None，不让异常穿透到前端。
"""

from __future__ import annotations

import logging
from typing import Any

import requests

from ..settings import load

logger = logging.getLogger(__name__)

DEFAULT_BASE_URLS = {
    "openai": "https://api.openai.com/v1",
    "deepseek": "https://api.deepseek.com/v1",
    "dashscope": "https://dashscope.aliyuncs.com/compatible-mode/v1",
}


def is_available() -> bool:
    return bool(load().api_key())


def complete(
    *,
    system_prompt: str,
    user_message: str,
    history: list[dict[str, str]] | None = None,
) -> str | None:
    settings = load()
    api_key = settings.api_key()
    if not api_key:
        return None

    messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
    for item in (history or [])[-8:]:
        role = item.get("role")
        content = (item.get("content") or "").strip()
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_message})

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
        payload: dict[str, Any] = response.json()
        content = payload["choices"][0]["message"]["content"]
        if isinstance(content, str) and content.strip():
            return content.strip()
        logger.warning("模型返回了空内容")
    except Exception as exc:
        logger.warning("调用模型失败：%s", exc)
    return None