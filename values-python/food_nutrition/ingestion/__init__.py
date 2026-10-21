#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据导入层：把外部营养数据源清洗后写入 MySQL。

当前只有 USDA FoodData Central 一个来源；以后接其他数据源时
在本包内新增模块，共用 config 与 db，不要把连接参数抄一遍。
"""