#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI 问答层。

已实现：
    retrieval.py  从 MySQL 营养库检索食物、营养素、排名与富含判定规则
    chat.py       生成回答：有模型 Key 时调用模型，否则用库中数据直接作答
    server.py     FastAPI 服务，接口结构与 Java 的 /api/assistant/chat 一致
    settings.py   模型供应商与凭据配置（只读环境变量）

为什么单独成包而不是塞进 ingestion/images：
营养数据的清洗是确定性任务，AI 问答是非确定性任务，两者的依赖体积、
失败重试策略、可观测性要求完全不同。分开放，才能让数据脚本保持轻依赖
（pymysql / requests / Pillow），AI 依赖通过 requirements-ai.txt 单独安装。

尚未使用的骨架：
    tools/   预留给 Agent 工具注册
    chains/  预留给 LangChain 组合
    graphs/  预留给 LangGraph 状态机
    memory/  预留给会话级记忆
"""


def __getattr__(name: str):
    """延迟导入：只有真正访问子模块时才加载，避免未安装 AI 依赖时 import 失败。"""
    import importlib

    if name in {"settings", "retrieval", "chat", "server", "chains", "graphs", "tools", "memory"}:
        return importlib.import_module(f"{__name__}.{name}")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")