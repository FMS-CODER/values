#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI 问答层。

模块划分：
    retrieval.py  从 MySQL 营养库检索食物、营养素、排名与富含判定规则
    chat.py       旧版 answer() 兼容入口，实际委托给 services/chat_service.py
    server.py     FastAPI 服务，接口结构与 Java 的 /api/assistant/chat 一致
    settings.py   模型、嵌入与向量库配置（只读环境变量）
    rag/          知识切块、向量化、Qdrant 存取、检索与索引导入
    agents/       协调器、营养数据、知识检索、营养分析与答案审核
    services/     知识检索服务、问答流程与模型客户端

为什么单独成包而不是塞进 ingestion/images：
营养数据的清洗是确定性任务，AI 问答是非确定性任务，两者的依赖体积、
失败重试策略、可观测性要求完全不同。分开放，才能让数据脚本保持轻依赖
（pymysql / requests / Pillow），AI 依赖通过 requirements-ai.txt 单独安装。
"""


def __getattr__(name: str):
    """延迟导入：只有真正访问子模块时才加载，避免未安装 AI 依赖时 import 失败。"""
    import importlib

    if name in {"settings", "retrieval", "chat", "server", "rag", "agents", "services"}:
        return importlib.import_module(f"{__name__}.{name}")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")