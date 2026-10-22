#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""旧版问答入口的兼容层。

实际流程已经迁移到 services/chat_service.py 与 agents/：
- 保留 answer(message, history) 的旧签名，避免已有调用方（HTTP 层、脚本）失效；
- 新代码应直接注入 ChatService，以拿到 citations、intent 等结构化结果。
"""

from __future__ import annotations

from .services.chat_service import ChatResult, ChatService, SUGGESTIONS

_service: ChatService | None = None


def get_chat_service() -> ChatService:
    global _service
    if _service is None:
        _service = ChatService()
    return _service


def answer(
    message: str,
    history: list[dict[str, str]] | None = None,
) -> tuple[str, str, list[str]]:
    """返回 (reply, mode, suggestions)。"""
    result: ChatResult = get_chat_service().answer(message, history)
    return result.reply, result.mode, result.suggestions


__all__ = ["answer", "get_chat_service", "ChatResult", "ChatService", "SUGGESTIONS"]