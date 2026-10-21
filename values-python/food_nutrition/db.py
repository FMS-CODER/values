#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据库连接工厂。

脚本与以后的 AI 工具层都从这里取连接，避免每处 new 一次 connect 时
漏掉 charset/游标类型，导致中文乱码或返回 tuple 而非 dict。
"""

from __future__ import annotations

import pymysql

from .config import db_config


def connect(*, dict_cursor: bool = True, autocommit: bool = True, **overrides) -> pymysql.connections.Connection:
    """建立连接。

    :param dict_cursor: 查询结果是否返回 dict；按列名取值比按下标更不易出错
    :param overrides: 覆盖配置里的 host/port/user/password/database（对应命令行参数）
    """
    config = db_config()
    config.update({key: value for key, value in overrides.items() if value is not None})

    return pymysql.connect(
        charset="utf8mb4",
        autocommit=autocommit,
        cursorclass=pymysql.cursors.DictCursor if dict_cursor else pymysql.cursors.Cursor,
        **config,
    )