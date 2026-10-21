#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""食物图片体检脚本（只读：不写库、不下载、不改文件）。

用途：在跑批量补全前后各跑一次，回答四个问题——
  1) 有多少食物缺图（image_url 为空）；
  2) 有 image_url 的，本地文件是否真的存在、能否解码；
  3) 图片目录里有没有没人引用的冗余文件；
  4) 库里的 /foods/xxx 路径与前端目录是怎么对应的。

路径对应关系是固定的：image_url = "/foods/apple.jpg" → values-front/public/foods/apple.jpg。
判断依据是「去掉开头斜杠后拼到 values-front/public 下」，不维护第二份映射表。

用法：python -m food_nutrition images-check
"""

import argparse
import os
import sys

import pymysql
from PIL import Image

from ..config import FOOD_IMAGE_DIR, REPO_ROOT as PROJECT_ROOT, db_config

# Windows 控制台默认可能是 GBK，食物名是中文，统一切到 UTF-8 输出。
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# 路径全部来自 config：图片目录与数据库参数都不在脚本里写死
PUBLIC_DIR = str(FOOD_IMAGE_DIR.parent)
FOODS_DIR = str(FOOD_IMAGE_DIR)

# 前端代码里引用的占位图，不算冗余
PLACEHOLDER = "placeholder.svg"

DB_DEFAULTS = db_config()


def connect(args):
    return pymysql.connect(
        host=args.host, port=args.port, user=args.user, password=args.password,
        database=args.database, charset="utf8mb4", autocommit=True,
        cursorclass=pymysql.cursors.DictCursor,
    )


def map_to_local(image_url):
    """把库里的 image_url 换算成本地文件路径。"""
    if not image_url:
        return None
    return os.path.join(PUBLIC_DIR, image_url.lstrip("/"))


def is_decodable(path):
    """能否被 Pillow 解码；verify() 会消费文件对象，所以成功后要重新 open 才算数。"""
    try:
        with Image.open(path) as img:
            img.verify()
        with Image.open(path) as img:
            img.load()
        return True, ""
    except Exception as exc:  # 损坏文件、不支持格式、权限问题都会走到这里
        return False, str(exc)[:80]


def load_foods(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT id, name, name_en, image_url FROM food ORDER BY id")
        return cur.fetchall()


def collect(conn):
    """汇总所有体检数据，返回结构化字典，供 report() 打印。"""
    foods = load_foods(conn)
    null_ids = [f for f in foods if not f["image_url"]]

    referenced_rel = set()
    missing_file = []      # 有 image_url 但本地文件不存在
    broken_file = []       # 文件存在但无法解码
    ok_rows = []           # 路径与文件都正常
    for f in foods:
        if not f["image_url"]:
            continue
        rel = f["image_url"].lstrip("/")
        referenced_rel.add(os.path.basename(rel))
        local = map_to_local(f["image_url"])
        if not os.path.isfile(local):
            missing_file.append((f, local))
            continue
        ok, err = is_decodable(local)
        if ok:
            ok_rows.append((f, local, os.path.getsize(local)))
        else:
            broken_file.append((f, local, err))

    # 目录里存在、但没有任何 food.image_url 指向的文件（排除前端占位图）
    on_disk = set()
    if os.path.isdir(FOODS_DIR):
        for name in os.listdir(FOODS_DIR):
            path = os.path.join(FOODS_DIR, name)
            if os.path.isfile(path):
                on_disk.add(name)
    unreferenced = sorted(n for n in on_disk if n not in referenced_rel and n != PLACEHOLDER)
    orphan_referenced = sorted(n for n in referenced_rel if n not in on_disk)  # 引用但缺失

    return {
        "foods": foods,
        "null_ids": null_ids,
        "missing_file": missing_file,
        "broken_file": broken_file,
        "ok_rows": ok_rows,
        "unreferenced": unreferenced,
        "on_disk_count": len(on_disk),
        "orphan_referenced": orphan_referenced,
    }


def report(args, conn=None):
    own_conn = conn is None
    if own_conn:
        conn = connect(args)
    try:
        data = collect(conn)
    finally:
        if own_conn:
            conn.close()

    total = len(data["foods"])
    print("=" * 76)
    print("食物图片体检（只读，不写库不下载）")
    print("=" * 76)
    print("前端图片目录 : %s" % FOODS_DIR)
    print("路径对应规则 : image_url '/foods/x' → values-front/public/foods/x")
    print()
    print("① 统计")
    print("  食物总数                    : %d" % total)
    print("  image_url 为空（缺图）      : %d" % len(data["null_ids"]))
    print("  有 image_url 且文件正常     : %d" % len(data["ok_rows"]))
    print("  有 image_url 但本地文件缺失 : %d %s"
          % (len(data["missing_file"]), [f["id"] for f, _ in data["missing_file"]] or ""))
    print("  文件存在但无法解码          : %d %s"
          % (len(data["broken_file"]), [f["id"] for f, _, _ in data["broken_file"]] or ""))
    print("  目录内文件总数              : %d" % data["on_disk_count"])
    print("  未被任何食物引用的冗余图片  : %d %s" % (len(data["unreferenced"]), data["unreferenced"] or ""))
    print("  被引用但目录里不存在的文件  : %d %s"
          % (len(data["orphan_referenced"]), data["orphan_referenced"] or ""))

    print()
    print("② 已有图片的食物 → 本地文件对应表")
    print("  %-4s %-10s %-26s %-9s %s" % ("id", "名称", "image_url", "体积KB", "本地文件"))
    for f, local, size in data["ok_rows"]:
        print("  %-4s %-10s %-26s %-9.1f %s"
              % (f["id"], f["name"], f["image_url"], size / 1024.0, os.path.relpath(local, PROJECT_ROOT)))

    if data["missing_file"] or data["broken_file"]:
        print()
        print("③ 异常明细")
        for f, local in data["missing_file"]:
            print("  [缺失] id=%-4s %-10s %s" % (f["id"], f["name"], os.path.relpath(local, PROJECT_ROOT)))
        for f, local, err in data["broken_file"]:
            print("  [损坏] id=%-4s %-10s %s (%s)" % (f["id"], f["name"], os.path.relpath(local, PROJECT_ROOT), err))

    print()
    print("④ 缺图食物 id（前 20 个）：%s%s"
          % ([f["id"] for f in data["null_ids"][:20]], " ..." if len(data["null_ids"]) > 20 else ""))
    return data


def main():
    ap = argparse.ArgumentParser(description="食物图片体检（只读）")
    ap.add_argument("--host", default=DB_DEFAULTS["host"])
    ap.add_argument("--port", type=int, default=DB_DEFAULTS["port"])
    ap.add_argument("--user", default=DB_DEFAULTS["user"])
    ap.add_argument("--password", default=DB_DEFAULTS["password"])
    ap.add_argument("--database", default=DB_DEFAULTS["database"])
    report(ap.parse_args())


if __name__ == "__main__":
    main()