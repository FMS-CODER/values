#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI 营养问答 HTTP 服务。

接口与 Java 侧的 /api/assistant/chat 保持完全一致的请求/响应结构，

启动：
    python -m food_nutrition ai-serve
    python -m food_nutrition.ai.server --port 8000

依赖：
    pip install -r requirements-ai.txt
"""

from __future__ import annotations

import argparse
import logging
import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .chat import get_chat_service

logger = logging.getLogger(__name__)

MAX_MESSAGE_LENGTH = 1000
MAX_HISTORY_SIZE = 20


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] | None = None


class CitationModel(BaseModel):
    documentId: str
    title: str
    source: str
    url: str = ""
    snippet: str
    score: float
    kind: str = "knowledge"
    reviewStatus: str = "approved"
    version: str = "1"


class ChatResponse(BaseModel):
    reply: str
    mode: str
    suggestions: list[str]
    citations: list[CitationModel] = []
    intent: str = "general"


app = FastAPI(title="食物营养百科 AI 服务", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    """Java 侧与运维脚本用这个接口判断服务是否就绪。"""
    return {"status": "ok"}


@app.post("/api/assistant/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    message = (payload.message or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="message 不能为空")
    if len(message) > MAX_MESSAGE_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"message 长度不能超过 {MAX_MESSAGE_LENGTH} 个字符",
        )

    history = payload.history or []
    if len(history) > MAX_HISTORY_SIZE:
        raise HTTPException(status_code=400, detail=f"history 最多 {MAX_HISTORY_SIZE} 条")
    for item in history:
        if item.role not in ("user", "assistant"):
            raise HTTPException(status_code=400, detail="history.role 只能是 user 或 assistant")

    try:
        result = get_chat_service().answer(
            message,
            [{"role": item.role, "content": item.content} for item in history],
        )
    except Exception as exc:
        # 数据库不可用等基础设施问题返回 503，Java 侧会回退到占位回复
        logger.exception("生成回答失败：%s", exc)
        raise HTTPException(status_code=503, detail="AI 服务暂时不可用") from exc

    return ChatResponse(
        reply=result.reply,
        mode=result.mode,
        suggestions=result.suggestions,
        citations=[CitationModel(**citation.to_dict()) for citation in result.citations],
        intent=result.intent,
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="启动食物营养百科 AI 问答服务")
    parser.add_argument(
        "--host",
        default=os.getenv("AI_SERVICE_HOST", "127.0.0.1"),
        help="监听地址，默认 127.0.0.1",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("AI_SERVICE_PORT", "8000")),
        help="监听端口，默认 8000",
    )
    args = parser.parse_args(argv)

    import uvicorn

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()