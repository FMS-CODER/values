#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""统一日志配置。

现有脚本以 print 为主（面向人的命令行输出），这里提供 configure() 是为了
后续 AI 服务层（LangGraph 节点、工具调用）能复用同一套格式，而不是各写一份。
"""

from __future__ import annotations

import logging
import sys


def configure(level: int = logging.INFO) -> None:
    """配置根日志器；重复调用不会叠加 handler。"""
    root = logging.getLogger()
    if root.handlers:
        root.setLevel(level)
        return

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)-5s %(name)s - %(message)s",
            datefmt="%H:%M:%S",
        )
    )
    root.addHandler(handler)
    root.setLevel(level)