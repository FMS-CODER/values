#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""图片处理层：候选搜索、初筛、下载转码、审核清单。

模块职责：
    providers  三方图片源的统一接口与限流
    fetch      批量补全主流程
    check      只读体检（缺图/失效/冗余）
"""