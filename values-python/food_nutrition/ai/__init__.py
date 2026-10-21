#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI 扩展层（预留）。

当前只有目录骨架，**没有安装也没有导入** LangChain / LangGraph，
因此不会影响现有数据脚本的运行。

为什么单独成包而不是塞进 ingestion/images：
营养数据的清洗是确定性任务，AI 问答是非确定性任务，两者的依赖体积、
失败重试策略、可观测性要求完全不同。分开放，才能让数据脚本保持轻依赖
（pymysql / requests / Pillow），AI 依赖通过 requirements-ai.txt 单独安装。

规划中的职责：
    tools/   把「查食物详情、查营养素、按条件筛选」包装成 Agent 可调用的工具
    chains/  单步或少步的 LangChain 组合（例如把查询结果改写成营养说明）
    graphs/  LangGraph 状态机（例如 意图识别 → 工具调用 → 结果校验 → 生成回答）
    memory/  会话级记忆（多轮追问同一食物时保留上下文）
"""


def __getattr__(name: str):
    """延迟导入：只有真正访问子模块时才加载，避免未安装 AI 依赖时 import 失败。"""
    import importlib

    if name in {"settings", "chains", "graphs", "tools", "memory"}:
        return importlib.import_module(f"{__name__}.{name}")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")