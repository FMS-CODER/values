#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""命令行总入口。

为什么要有它：
各业务脚本自己带 argparse，直接 `python -m food_nutrition.images.fetch` 也能跑；
这里再加一层是为了让使用者不必记住模块路径，并且以后接 AI 命令时
（例如 `python -m food_nutrition ai.ask`）有统一的扩展位置。

注意：转发时改写 sys.argv 而不是把参数对象传进去，
因为子模块的 argparse 是自己从 sys.argv 读取的，改写后子命令的 --help 也能正常工作。
"""

from __future__ import annotations

import importlib
import sys

COMMANDS: dict[str, tuple[str, str]] = {
    "ingest": ("food_nutrition.ingestion.usda_foundation", "USDA Foundation 营养数据导入（--check/--dry-run/--apply/--verify）"),
    "images-check": ("food_nutrition.images.check", "食物图片体检（只读，不写库不下载）"),
    "images-fetch": ("food_nutrition.images.fetch", "食物图片批量补全（搜索/下载/转码/写库）"),
}


def _print_help() -> None:
    print("用法：python -m food_nutrition <命令> [参数...]\n")
    print("可用命令：")
    for name, (_, desc) in COMMANDS.items():
        print(f"  {name:<14} {desc}")
    print("\n示例：")
    print("  python -m food_nutrition images-check")
    print("  python -m food_nutrition images-fetch --scan")
    print("  python -m food_nutrition ingest --check")
    print("\n每个命令的完整参数用：python -m food_nutrition <命令> --help")


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)

    if not args or args[0] in ("-h", "--help", "help"):
        _print_help()
        return 0

    name = args[0]
    if name not in COMMANDS:
        print(f"未知命令：{name}\n", file=sys.stderr)
        _print_help()
        return 2

    module_path, _ = COMMANDS[name]
    module = importlib.import_module(module_path)

    # 让子模块的 argparse 看到「命令之后」的参数
    sys.argv = [module_path, *args[1:]]
    module.main()
    return 0