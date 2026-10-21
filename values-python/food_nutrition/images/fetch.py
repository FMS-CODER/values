#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""食品图片批量补全主脚本（搜索 → 初筛 → 下载 → 校验转码 → 写库 → 记录）。

设计要点（每条都标注了「为什么」）：
- 权威映射是数据库 food.image_url：补全成功后只回写这一列，绝不维护第二份「食物→图片」表，
  避免两处不一致；且只更新原本为空的列，不覆盖已有的非空值。
- 搜索 API 串行 + 1.2s 节流（在 providers.py 统一实现），下载才用 4 线程：搜索被限速，
  并发搜索只会更快撞 429；下载是 IO 密集且各站点独立，可以并发。
- 文件名用 {food_id}-{slug}.webp：food_id 是稳定主键，slug 由 name_en 生成，两者合起来
  既不撞名也不受中文影响，重跑时能据此判断文件是否已存在，从而做到幂等。
- 缩略图统一进 512×512 等比盒：卡片 128px、详情页大图 176px，按 3 倍屏算 176×3≈528，
  512 足够清晰且体积可控；只缩不放，避免把低清图拉花。
- 自动匹配的 review_status 一律 pending：脚本没有能力判断「图对不对」，只做机器初筛，
  最终由人看图确认，所以绝不自动置为 approved。

用法：
    python -m food_nutrition images-fetch --scan
    python -m food_nutrition images-fetch --provider commons --limit 5
    python -m food_nutrition images-fetch --review 45 rejected
"""

import argparse
import concurrent.futures
import csv
import io
import os
import re
import sys
import time

import pymysql
import requests
from PIL import Image

# 同包模块：check 负责路径换算/可解码判定，providers 负责三方搜索
from . import check
from .providers import DOWNLOAD_HEADERS, MissingKeyError, select_provider
from ..config import (
    DATA_DIR as CONFIG_DATA_DIR,
    FOOD_IMAGE_DIR,
    IMAGE_MANIFEST,
    IMAGE_MAPPINGS_DIR,
    REJECTED_CANDIDATES,
    REPO_ROOT as PROJECT_ROOT,
    REVIEW_NEEDED,
    db_config,
)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# 路径统一由 config 提供：代码与运行产物分离，脚本移动后仍能定位
PUBLIC_DIR = str(FOOD_IMAGE_DIR.parent)
FOODS_DIR = str(FOOD_IMAGE_DIR)
MAPPINGS_DIR = str(IMAGE_MAPPINGS_DIR)
DATA_DIR = str(CONFIG_DATA_DIR)

MANIFEST_PATH = str(IMAGE_MANIFEST)
REVIEW_PATH = str(REVIEW_NEEDED)
REJECTED_PATH = str(REJECTED_CANDIDATES)
KEYWORDS_PATH = os.path.join(MAPPINGS_DIR, "keywords.json")

MANIFEST_COLUMNS = ["food_id", "food_name", "local_path", "source_name", "source_url",
                    "photographer", "license", "attribution", "download_status", "review_status"]
REVIEW_COLUMNS = ["food_id", "food_name", "search_term", "matched_title", "local_path",
                  "source_url", "license", "reason"]
REJECTED_COLUMNS = ["food_id", "food_name", "search_term", "title", "source_name",
                    "source_url", "reason"]
MANUAL_COLUMNS = ["food_id", "image_url", "source_name", "source_url", "photographer",
                  "license", "attribution"]

DB_DEFAULTS = db_config()

SEARCH_LIMIT = 15              # 每个食物取多少条候选
MAX_DOWNLOAD_BYTES = 8 * 1024 * 1024
MIN_EDGE = 200                 # 最短边下限
MAX_ASPECT = 4.0               # 极端长宽比上限
THUMB_BOX = (512, 512)
WEBP_QUALITY = 82
WEBP_METHOD = 6
DOWNLOAD_WORKERS = 4
DOWNLOAD_TIMEOUT = (10, 20)
DOWNLOAD_RETRIES = 2
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP", "BMP", "GIF"}
UA = DOWNLOAD_HEADERS  # 与搜索共用同一 UA，避免下载主机按笼统 UA 限速

# name_en 推导搜索词用的词表
GENERIC_HEADS = {"nuts", "fish", "seeds", "oil", "milk", "cheese", "rice", "flour", "beans",
                 "egg", "eggs", "peppers", "squash", "melons", "sauce", "cookies", "sugars",
                 "crustaceans", "spices", "fats"}
QUALIFIER_HEADS = {"chicken", "beef", "pork", "turkey", "lamb", "veal", "duck"}
STATE_WORDS = {"raw", "cooked", "frozen", "canned", "dried", "dry", "enriched", "unenriched",
               "bleached", "fresh", "whole", "mature", "baby", "ripe", "unripe", "unsweetened",
               "sweetened", "plain", "refrigerated", "pasteurized", "cured", "smoked",
               "ready-to-serve", "ready to serve", "shelf stable", "seedless", "without skin",
               "with peel", "includes skin", "with skin", "boneless", "skinless",
               "meat and skin", "meat only", "flesh only", "no pulp", "commercial",
               "extra virgin", "part-skim", "low moisture", "sliced", "restaurant"}

_ALNUM = re.compile(r"[a-z0-9]+")


# --------------------------------------------------------------------------
# 基础工具
# --------------------------------------------------------------------------
def connect(args):
    return pymysql.connect(
        host=args.host, port=args.port, user=args.user, password=args.password,
        database=args.database, charset="utf8mb4", autocommit=False,
        cursorclass=pymysql.cursors.DictCursor,
    )


def slugify(name_en):
    """name_en → 文件名 slug：小写、非字母数字转 '-'、压缩连续 '-'、截断 ≤40。"""
    text = (name_en or "").lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text[:40].strip("-") or "food"


def _is_composition(part):
    """判断逗号分段是不是成分/规格描述（含数字、百分号、括号、with added 等）。"""
    if not part:
        return True
    if any(ch.isdigit() for ch in part) or "%" in part or "(" in part:
        return True
    return "with added" in part


def derive_search_term(name_en, override):
    """按 keywords.json 的说明推导搜索词；override 里有 search_term 则直接采用。"""
    if override and override.get("search_term"):
        return override["search_term"]
    parts = [p.strip().lower() for p in (name_en or "").split(",") if p.strip()]
    if not parts:
        return ""
    head = parts[0]
    meaningful = [p for p in parts[1:] if p not in STATE_WORDS and not _is_composition(p)]
    if head in GENERIC_HEADS:
        return meaningful[0] if meaningful else head
    if head in QUALIFIER_HEADS and meaningful:
        return "%s %s" % (head, meaningful[0])
    return head


def _stem(word):
    """极简词干化：去掉复数尾 s，让 apple 与 apples 互相命中。"""
    return word[:-1] if word.endswith("s") and len(word) > 3 else word


def _words(text):
    return {_stem(w) for w in _ALNUM.findall((text or "").lower())}


def load_keywords():
    import json
    with open(KEYWORDS_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_csv_rows(path, columns):
    """读 CSV 为 dict 列表；文件不存在返回空。供上次运行结果复用。"""
    if not os.path.isfile(path):
        return []
    with open(path, newline="", encoding="utf-8-sig") as f:
        return [row for row in csv.DictReader(f) if row.get(columns[0])]


def write_csv(path, columns, rows):
    """整表重写（先临时文件再替换），保证幂等：不追加、不重复。"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({c: row.get(c, "") for c in columns})
    os.replace(tmp, path)


def local_decodable(path):
    if not os.path.isfile(path):
        return False
    return check.is_decodable(path)[0]


# --------------------------------------------------------------------------
# 候选初筛与打分
# --------------------------------------------------------------------------
def classify_candidates(candidates, term, exclude_words):
    """返回 (accepted[(score, cand)], rejected[(cand, reason)])。

    排除词按词边界匹配，避免 mango 命中 man；正向分看标题命中、分辨率、许可。
    """
    kw = {_stem(t) for t in _ALNUM.findall(term.lower())}
    accepted, rejected = [], []
    patterns = [re.compile(r"\b%s\b" % re.escape(w.lower())) for w in exclude_words if w]
    for cand in candidates:
        hay = (cand.title or "").lower()
        hit = next((p for p in patterns if p.search(hay)), None)
        if hit:
            rejected.append((cand, "命中排除词:%s" % hit.pattern.strip("\\b")))
            continue
        if not cand.download_url:
            rejected.append((cand, "无下载地址"))
            continue
        if cand.mime and not cand.mime.startswith("image/"):
            rejected.append((cand, "非图片MIME:%s" % cand.mime))
            continue
        if cand.width and cand.height and min(cand.width, cand.height) < MIN_EDGE:
            rejected.append((cand, "分辨率过低:%dx%d" % (cand.width, cand.height)))
            continue

        wordset = _words(cand.title)
        matched = kw & wordset
        score = 3 * len(matched)
        if len(matched) >= 2:
            score += 2
        if cand.width >= 400 and cand.height >= 400:
            score += 2
        if cand.width >= 800:
            score += 1
        lic = (cand.license or "").lower()
        if lic.startswith("cc") or "public" in lic or "cc0" in lic:
            score += 1
        accepted.append((score, cand))

    accepted.sort(key=lambda x: (-x[0], -(x[1].width or 0)))
    return accepted, rejected


# --------------------------------------------------------------------------
# 下载与转码
# --------------------------------------------------------------------------
def download_bytes(url, session):
    """返回 (ok, reason, data)。200/图片类型/非 HTML/≤8MB，失败退避重试 2 次。"""
    last_err = "未知错误"
    for attempt in range(DOWNLOAD_RETRIES + 1):
        try:
            resp = session.get(url, timeout=DOWNLOAD_TIMEOUT, headers=UA, stream=True)
        except requests.RequestException as exc:
            last_err = "网络错误:%s" % str(exc)[:70]
            time.sleep(1.5 * (attempt + 1))
            continue
        if resp.status_code == 429 or resp.status_code >= 500:
            last_err = "HTTP %d" % resp.status_code
            time.sleep(2.0 * (attempt + 1))
            continue
        if resp.status_code != 200:
            return False, "HTTP %d" % resp.status_code, None

        ctype = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        chunks, size = [], 0
        for chunk in resp.iter_content(65536):
            size += len(chunk)
            if size > MAX_DOWNLOAD_BYTES:
                return False, "超过%dMB上限" % (MAX_DOWNLOAD_BYTES // 1024 // 1024), None
            chunks.append(chunk)
        data = b"".join(chunks)
        if not data:
            return False, "空响应", None
        if ctype and not ctype.startswith("image/") and ctype != "application/octet-stream":
            return False, "Content-Type非图片:%s" % ctype, None
        head = data[:512].lstrip().lower()
        if head.startswith(b"<!doctype") or head.startswith(b"<html") or head.startswith(b"<"):
            return False, "内容是HTML错误页", None
        return True, "", data
    return False, last_err, None


def process_to_webp(data):
    """Pillow 校验后等比缩进 512 盒、转 WebP。返回 (bytes, reason)。"""
    try:
        with Image.open(io.BytesIO(data)) as probe:
            probe.verify()          # verify 只检查完整性，不真正解码
        img = Image.open(io.BytesIO(data))
        img.load()                  # verify 之后必须重新打开并 load 才能拿到像素
    except Exception as exc:
        return None, "无法解码:%s" % str(exc)[:60]

    if img.format not in ALLOWED_FORMATS:
        return None, "不支持的格式:%s" % img.format
    width, height = img.size
    if min(width, height) < MIN_EDGE:
        return None, "尺寸过小:%dx%d" % (width, height)
    if max(width, height) / max(1, min(width, height)) > MAX_ASPECT:
        return None, "长宽比过大:%dx%d" % (width, height)

    # 保留透明度：带 alpha 通道或 PNG 透明色 → RGBA，其余 RGB（WebP 支持 alpha）
    keep_alpha = img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info)
    img = img.convert("RGBA" if keep_alpha else "RGB")
    resample = getattr(Image, "Resampling", Image).LANCZOS
    img.thumbnail(THUMB_BOX, resample)   # thumbnail 只缩不放
    buf = io.BytesIO()
    img.save(buf, format="WEBP", quality=WEBP_QUALITY, method=WEBP_METHOD)
    return buf.getvalue(), ""


def atomic_write(path, data):
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(data)
    os.replace(tmp, path)   # 原子替换：不会留下半截文件


def download_job(job):
    """worker：下载 + 转码 + 落盘。返回结果 dict。"""
    session = requests.Session()
    ok, reason, data = download_bytes(job["download_url"], session)
    if not ok:
        return dict(food_id=job["food_id"], status="failed", reason=reason)
    webp, reason = process_to_webp(data)
    if webp is None:
        return dict(food_id=job["food_id"], status="failed", reason=reason)
    atomic_write(job["dest_path"], webp)
    return dict(food_id=job["food_id"], status="downloaded", reason="", size=len(webp))


# --------------------------------------------------------------------------
# 目标规划
# --------------------------------------------------------------------------
def plan_targets(data, args, prev_manifest, refetch_ids=(), hold_ids=()):
    """把食物分成：已有有效图（existing）/ 目标文件已存在（skipped）/ 需要下载（jobs）。

    refetch_ids（--refetch-rejected）：人工已判为 rejected 的食物要重取，必须绕过
    「已有有效图」和「目标文件已存在」两道跳过，否则改了搜索词也永远不会重新下载。
    hold_ids（人工已置空的 rejected）：这些食物是「看了两次都不合适，宁可没图」的结论，
    默认必须继续待着，不能被本次运行重新塞回一张图。
    """
    existing, skipped, jobs = [], [], []
    prev_by_id = {r["food_id"]: r for r in prev_manifest}
    refetch_ids = {str(i) for i in refetch_ids}
    hold_ids = {str(i) for i in hold_ids}

    for food in data["foods"]:
        fid = str(food["id"])
        if fid in hold_ids:
            continue          # 人工判定无合适图：不重新检索、不写库、不复活
        db_local = check.map_to_local(food["image_url"]) if food["image_url"] else None
        if fid not in refetch_ids and food["image_url"] and db_local and local_decodable(db_local):
            existing.append(food)
            continue

        # 目标文件名只由 id + name_en 决定，无需先搜索就能判断是否已存在
        slug = slugify(food["name_en"])
        dest = os.path.join(FOODS_DIR, "%s-%s.webp" % (food["id"], slug))
        if fid not in refetch_ids and local_decodable(dest):
            skipped.append((food, "/foods/%s-%s.webp" % (food["id"], slug)))
            continue
        jobs.append((food, dest))

    # 过滤：--only-food-ids / --retry-failed / --limit
    if args.only_food_ids:
        allow = {s.strip() for s in args.only_food_ids.split(",") if s.strip()}
        jobs = [j for j in jobs if str(j[0]["id"]) in allow]
    if args.retry_failed:
        failed_ids = {fid for fid, r in prev_by_id.items() if r.get("download_status") == "failed"}
        jobs = [j for j in jobs if str(j[0]["id"]) in failed_ids]
    if args.limit:
        jobs = jobs[: args.limit]
    return existing, skipped, jobs


# --------------------------------------------------------------------------
# 主流程
# --------------------------------------------------------------------------
def run_fetch(args):
    try:
        provider = select_provider(args.provider)
    except MissingKeyError as exc:
        print("=" * 76)
        print("无法开始：%s" % exc)
        print("可选做法：")
        print("  1) 设置对应环境变量后重试（PowerShell：$env:PEXELS_API_KEY='你的Key'）")
        print("  2) 改用无需 Key 的 Commons：--provider commons")
        print("  3) 拿不到 Key 时用 --manual-urls <csv> 从清单导入图片 URL")
        print("（本次未做任何下载，也没有写库，不存在伪造的成功结果。）")
        return 2

    print("使用 provider: %s（requires_key=%s）" % (provider.name, provider.requires_key))

    keywords = load_keywords()
    exclude_words = list(keywords.get("exclude_words", []))
    overrides = keywords.get("search_term_overrides", {})

    conn = connect(args)
    try:
        data = check.collect(conn)
        prev_manifest = load_csv_rows(MANIFEST_PATH, MANIFEST_COLUMNS)
        prev_review = {r["food_id"]: r for r in load_csv_rows(REVIEW_PATH, REVIEW_COLUMNS)}
        prev_by_id = {r["food_id"]: r for r in prev_manifest}

        # 人工审核结论的两种用法：
        #   ① --refetch-rejected：把已判 rejected 的食物强制重取（绕过所有跳过）；
        #   ② 默认：已判 rejected 且已置空（local_path 为空）的食物保持「无图」结论，不再自动补。
        refetch_ids = set()
        if args.refetch_rejected:
            refetch_ids = {fid for fid, r in prev_by_id.items() if r.get("review_status") == "rejected"}
            print("--refetch-rejected：将从 manifest 强制重取 %d 个已判 rejected 的食物 %s"
                  % (len(refetch_ids), sorted(refetch_ids, key=lambda x: int(x))))
        hold_ids = {fid for fid, r in prev_by_id.items()
                    if r.get("review_status") == "rejected" and not r.get("local_path")}
        hold_ids -= refetch_ids

        existing, skipped, jobs = plan_targets(data, args, prev_manifest, refetch_ids, hold_ids)
        print("食物总数 %d ｜ 原有有效图 %d ｜ 目标文件已存在(跳过下载) %d ｜ 本次需处理 %d"
              % (len(data["foods"]), len(existing), len(skipped), len(jobs)))

        rows = {}          # food_id → manifest 行
        review_rows = {}   # food_id → review 行
        rejected_rows = []

        # ① 已有有效图：区分「项目自带的既有资源」与「本脚本之前下载的图」
        for food in existing:
            fid = str(food["id"])
            prior = prev_by_id.get(fid) or {}
            if prior.get("local_path") == food["image_url"] and prior.get("source_name") not in ("", "existing"):
                # 这张图是本脚本早前下载的：沿用原始来源/许可，绝不改写成 unknown
                rows[fid] = {
                    "food_id": fid, "food_name": food["name"], "local_path": food["image_url"],
                    "source_name": prior["source_name"], "source_url": prior.get("source_url", ""),
                    "photographer": prior.get("photographer", ""), "license": prior.get("license", ""),
                    "attribution": prior.get("attribution", ""),
                    "download_status": prior.get("download_status") or "downloaded",
                    "review_status": prior.get("review_status") or "pending",
                }
            else:
                rows[fid] = {
                    "food_id": fid, "food_name": food["name"], "local_path": food["image_url"],
                    "source_name": "existing", "source_url": "", "photographer": "",
                    "license": "unknown", "attribution": "既有资源，来源与许可未记录",
                    "download_status": "existing", "review_status": "approved",
                }

        # ② 目标文件已存在：跳过下载，复用上次记录的来源信息
        for food, local_path in skipped:
            fid = str(food["id"])
            prior = prev_by_id.get(fid) or {}
            term = derive_search_term(food["name_en"], overrides.get(fid))
            rows[fid] = {
                "food_id": fid, "food_name": food["name"], "local_path": local_path,
                "source_name": prior.get("source_name", "unknown"),
                "source_url": prior.get("source_url", ""),
                "photographer": prior.get("photographer", ""),
                "license": prior.get("license", ""),
                "attribution": prior.get("attribution", "目标文件已存在，来源沿用上次记录"),
                "download_status": "skipped",
                "review_status": prior.get("review_status") or "pending",
            }
            if rows[fid]["review_status"] == "pending":
                pr = prev_review.get(fid) or {}
                review_rows[fid] = {
                    "food_id": fid, "food_name": food["name"],
                    "search_term": pr.get("search_term", term),
                    "matched_title": pr.get("matched_title", ""),
                    "local_path": local_path,
                    "source_url": rows[fid]["source_url"], "license": rows[fid]["license"],
                }

        # ③ 需要下载：串行搜索（节流），收集下载任务
        download_jobs, job_meta = [], {}
        for food, dest in jobs:
            fid = str(food["id"])
            term = derive_search_term(food["name_en"], overrides.get(fid))
            extra_exclude = overrides.get(fid, {}).get("extra_exclude_words", [])
            try:
                candidates = provider.search(term, SEARCH_LIMIT)
            except Exception as exc:
                rows[fid] = _failed_row(food, term, "搜索失败:%s" % str(exc)[:80])
                continue
            accepted, rejected = classify_candidates(candidates, term, exclude_words + extra_exclude)
            for cand, reason in rejected:
                rejected_rows.append({
                    "food_id": fid, "food_name": food["name"], "search_term": term,
                    "title": cand.title, "source_name": cand.provider,
                    "source_url": cand.source_url, "reason": reason,
                })
            if not accepted or accepted[0][0] < 3:
                # 得分 <3 说明标题里一个关键词都没命中，宁可判失败也不硬塞一张错图
                reason = "无可用候选(全部命中排除词或未命中关键词)" if not accepted else "候选均未命中关键词"
                rows[fid] = _failed_row(food, term, reason)
                continue
            best = accepted[0][1]
            for score, cand in accepted[1:]:
                rejected_rows.append({
                    "food_id": fid, "food_name": food["name"], "search_term": term,
                    "title": cand.title, "source_name": cand.provider,
                    "source_url": cand.source_url, "reason": "得分较低(score=%d)" % score,
                })
            local_path = "/foods/%s-%s.webp" % (food["id"], slugify(food["name_en"]))
            job_meta[fid] = dict(food=food, term=term, cand=best, local_path=local_path)
            download_jobs.append(dict(
                food_id=fid, download_url=best.download_url, dest_path=dest,
            ))

        # ④ 并发下载（搜索已串行完成，这里纯 IO）
        results = {}
        if download_jobs:
            print("开始下载 %d 张（%d 线程）……" % (len(download_jobs), DOWNLOAD_WORKERS))
            with concurrent.futures.ThreadPoolExecutor(max_workers=DOWNLOAD_WORKERS) as pool:
                for res in pool.map(download_job, download_jobs):
                    results[res["food_id"]] = res
                    if res["status"] == "downloaded":
                        print("  ✔ food_id=%s  %.1f KB" % (res["food_id"], res["size"] / 1024.0))
                    else:
                        print("  ✘ food_id=%s  %s" % (res["food_id"], res["reason"]))

        for fid, meta in job_meta.items():
            food, term, cand, local_path = meta["food"], meta["term"], meta["cand"], meta["local_path"]
            res = results.get(fid, {"status": "failed", "reason": "未执行"})
            if res["status"] == "downloaded":
                rows[fid] = {
                    "food_id": fid, "food_name": food["name"], "local_path": local_path,
                    "source_name": cand.provider, "source_url": cand.source_url,
                    "photographer": cand.photographer, "license": cand.license,
                    "attribution": _attribution(cand),
                    "download_status": "downloaded",
                    "review_status": "pending",   # 自动匹配一律待人工审核
                }
                review_rows[fid] = {
                    "food_id": fid, "food_name": food["name"], "search_term": term,
                    "matched_title": cand.title, "local_path": local_path,
                    "source_url": cand.source_url, "license": cand.license,
                }
            else:
                failed = _failed_row(food, term, res["reason"])
                # 保命：上次可能已审核，若本地确有可用文件则沿用上次状态
                prior = prev_by_id.get(fid) or {}
                failed["review_status"] = prior.get("review_status") or "n/a"
                rows[fid] = failed

        # ⑤ 未纳入本次处理范围的缺图食物：如实标记 missing，不伪造
        covered = set(rows.keys()) | {str(f["id"]) for f in data["foods"] if f["image_url"]}
        for food in data["foods"]:
            fid = str(food["id"])
            if fid in rows:
                continue
            if fid in hold_ids:
                # 人工已置空并判 rejected：沿用上次结论，绝不悄悄补一张图回来
                rows[fid] = dict(prev_by_id[fid])
                continue
            rows[fid] = {
                "food_id": fid, "food_name": food["name"], "local_path": "",
                "source_name": "", "source_url": "", "photographer": "", "license": "",
                "attribution": "未处理：本次未纳入处理范围",
                "download_status": "missing", "review_status": "n/a",
            }

        # ⑥ 写库：只更新成功的行、只更新原本为空的列（重取的食物允许覆盖）
        updated = write_db(conn, rows, refetch_ids)

        # ⑦ 记录：manifest 全量重写；rejected 累积去重（同一条候选不重复写，重跑不膨胀）
        manifest_rows = [rows[k] for k in sorted(rows, key=lambda x: int(x))]
        write_csv(MANIFEST_PATH, MANIFEST_COLUMNS, manifest_rows)
        # 待审核清单必须覆盖 manifest 里所有 pending 行（含历史遗留），检索信息优先取本次、其次取旧清单
        review_info = dict(prev_review)
        review_info.update(review_rows)
        review_list = build_review_list(manifest_rows, review_info)
        write_csv(REVIEW_PATH, REVIEW_COLUMNS, review_list)
        merged = {}
        for r in load_csv_rows(REJECTED_PATH, REJECTED_COLUMNS) + rejected_rows:
            merged[(r["food_id"], r["source_url"], r["title"], r["reason"])] = r
        rejected_all = sorted(merged.values(), key=lambda r: (int(r["food_id"]), r["reason"]))
        write_csv(REJECTED_PATH, REJECTED_COLUMNS, rejected_all)

        _print_summary(manifest_rows, review_list, rejected_all, updated)
        return 0
    finally:
        conn.close()


def build_review_list(manifest_rows, review_info):
    """review-needed = 需要人工跟进的条目：全部 pending 行 + 全部 rejected 行。

    检索信息（search_term / matched_title）优先取本次运行，其次取上次的待审核清单，
    这样历史遗留的 pending 行在重跑后也不会丢掉可核对的检索词。
    为什么把 rejected 也放进来：rejected 里既有「图被判错、需要换图」的，也有
    「换两次词仍不合适、已置空」的，两者都等人处理；后者的结论写在 reason 列里。
    """
    out = []
    for row in manifest_rows:
        status = row["review_status"]
        if status not in ("pending", "rejected"):
            continue
        info = review_info.get(row["food_id"]) or {}
        if status == "pending":
            reason = ""
        elif row["download_status"] == "rejected":
            reason = row["attribution"] or "人工判定无合适图片，已置空"
        else:
            reason = "人工判定图片不合适，待重新配图"
        out.append({
            "food_id": row["food_id"], "food_name": row["food_name"],
            "search_term": info.get("search_term", ""), "matched_title": info.get("matched_title", ""),
            "local_path": row["local_path"], "source_url": row["source_url"], "license": row["license"],
            "reason": reason,
        })
    return out


def _attribution(cand):
    """署名：作者 + 来源 + 许可。"""
    display = {"commons": "Wikimedia Commons", "pexels": "Pexels", "pixabay": "Pixabay"}
    parts = [p for p in [cand.photographer, display.get(cand.provider, cand.provider), cand.license] if p]
    return " / ".join(parts)


def _failed_row(food, term, reason):
    return {
        "food_id": str(food["id"]), "food_name": food["name"], "local_path": "",
        "source_name": "", "source_url": "", "photographer": "", "license": "",
        "attribution": "下载失败：%s" % reason,   # 表头固定，失败原因借用这一列承载
        "download_status": "failed", "review_status": "n/a",
    }


def write_db(conn, rows, overwrite_ids=()):
    """把成功的 /foods/xxx 回写 food.image_url；只更新原本为空的列，不覆盖非空值。

    唯一的例外是 overwrite_ids（本次 --refetch-rejected 的食物）：这些食物本来就带着
    一张被判错了的图，必须允许覆盖，否则改了搜索词也写不进新图。
    """
    overwrite_ids = {str(i) for i in overwrite_ids}
    pending, forced = [], []
    for fid, row in rows.items():
        if row["download_status"] in ("downloaded", "skipped") and row["local_path"]:
            (forced if fid in overwrite_ids else pending).append((row["local_path"], int(fid)))
    if not pending and not forced:
        return 0
    updated = 0
    try:
        with conn.cursor() as cur:
            for local_path, fid in pending:
                updated += cur.execute(
                    "UPDATE food SET image_url=%s WHERE id=%s AND (image_url IS NULL OR image_url='')",
                    (local_path, fid),
                )
            for local_path, fid in forced:
                updated += cur.execute(
                    "UPDATE food SET image_url=%s WHERE id=%s", (local_path, fid)
                )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return updated


def _print_summary(manifest_rows, review_list, rejected_rows, updated):
    status_count = {}
    for r in manifest_rows:
        status_count[r["download_status"]] = status_count.get(r["download_status"], 0) + 1
    failed = [r for r in manifest_rows if r["download_status"] == "failed"]
    print()
    print("=" * 76)
    print("补全完成统计")
    print("=" * 76)
    print("食物总数        : %d" % len(manifest_rows))
    print("原有有效        : %d" % status_count.get("existing", 0))
    print("本次成功下载    : %d" % status_count.get("downloaded", 0))
    print("跳过(文件已存在): %d" % status_count.get("skipped", 0))
    print("失败            : %d" % status_count.get("failed", 0))
    print("未处理(missing) : %d" % status_count.get("missing", 0))
    print("已置空(rejected): %d" % status_count.get("rejected", 0))
    if failed:
        grouped = {}
        for r in failed:
            reason = r["attribution"].replace("下载失败：", "")
            grouped.setdefault(reason, []).append(r["food_id"])
        print("  失败按原因分组：")
        for reason, ids in sorted(grouped.items(), key=lambda x: -len(x[1])):
            print("    %-40s %d 个: %s" % (reason, len(ids), ",".join(ids[:12]) + (" ..." if len(ids) > 12 else "")))
    print("待人工审核      : %d（见 %s）" % (len(review_list), os.path.relpath(REVIEW_PATH, PROJECT_ROOT)))
    print("被淘汰候选      : %d（见 %s）" % (len(rejected_rows), os.path.relpath(REJECTED_PATH, PROJECT_ROOT)))
    print("本次写库更新行数: %d" % updated)
    print("manifest        : %s（%d 行）" % (os.path.relpath(MANIFEST_PATH, PROJECT_ROOT), len(manifest_rows)))


# --------------------------------------------------------------------------
# 子命令：--scan / --review / --manual-urls
# --------------------------------------------------------------------------
def cmd_scan(args):
    conn = connect(args)
    try:
        check.report(args, conn)
    finally:
        conn.close()
    return 0


def cmd_review(args):
    food_id, status = str(args.review[0]), args.review[1].lower()
    if status not in ("approved", "rejected"):
        print("审核状态只能是 approved 或 rejected")
        return 2
    manifest = load_csv_rows(MANIFEST_PATH, MANIFEST_COLUMNS)
    if not manifest:
        print("manifest 不存在或为空，先跑一次补全")
        return 2
    prev_review = {r["food_id"]: r for r in load_csv_rows(REVIEW_PATH, REVIEW_COLUMNS)}
    hit = False
    for row in manifest:
        if row["food_id"] == food_id:
            row["review_status"] = status
            hit = True
    if not hit:
        print("manifest 里找不到 food_id=%s" % food_id)
        return 2
    manifest.sort(key=lambda r: int(r["food_id"]))
    write_csv(MANIFEST_PATH, MANIFEST_COLUMNS, manifest)

    # 同步 review-needed：pending 与 rejected 都要留（rejected 需人工换图/补图）
    review_rows = build_review_list(manifest, prev_review)
    write_csv(REVIEW_PATH, REVIEW_COLUMNS, review_rows)
    print("food_id=%s 审核状态已更新为 %s；需要人工跟进的清单剩 %d 行" % (food_id, status, len(review_rows)))
    if status == "rejected":
        print("提示：这只是标记。若要重取，请加 --refetch-rejected 重跑；"
              "若确认找不到合适图，请用 --clear-image %s 置空。" % food_id)
    return 0


def cmd_clear_image(args):
    """人工判定「找不到合适图」时置空：清 DB image_url + manifest 标 rejected。

    为什么只置空不删本地文件：置空后前端走占位图兜底，不会显示错图；保留文件是不破坏
    既有产物，check 模块会把它报成「冗余图片」，便于事后人工清理。
    为什么还要留 rejected+空 local_path：这是重跑时 hold 住该食物的凭据，
    否则下一次普通运行又会照着旧搜索词补一张错图回来。
    """
    entries = {}
    for raw in args.clear_image:
        fid, _, reason = str(raw).partition(":")
        if fid.strip():
            entries[fid.strip()] = reason.strip()
    manifest = load_csv_rows(MANIFEST_PATH, MANIFEST_COLUMNS)
    if not manifest:
        print("manifest 不存在或为空，先跑一次补全")
        return 2
    hit = []
    for row in manifest:
        if row["food_id"] in entries:
            reason = entries[row["food_id"]] or "自动匹配两次仍无合适图片，人工判定宁可无图"
            row["local_path"] = ""
            row["download_status"] = "rejected"
            row["review_status"] = "rejected"
            row["attribution"] = "已置空：%s" % reason
            hit.append(row["food_id"])
    absent = sorted(set(entries) - set(hit), key=lambda x: int(x))
    if absent:
        print("manifest 里找不到 food_id=%s" % ",".join(absent))
    if not hit:
        return 2
    manifest.sort(key=lambda r: int(r["food_id"]))
    write_csv(MANIFEST_PATH, MANIFEST_COLUMNS, manifest)

    conn = connect(args)
    try:
        with conn.cursor() as cur:
            for fid in hit:
                cur.execute("UPDATE food SET image_url=NULL WHERE id=%s", (int(fid),))
        conn.commit()
    finally:
        conn.close()

    prev_review = {r["food_id"]: r for r in load_csv_rows(REVIEW_PATH, REVIEW_COLUMNS)}
    review_rows = build_review_list(manifest, prev_review)
    write_csv(REVIEW_PATH, REVIEW_COLUMNS, review_rows)
    print("已置空 food_id=%s（image_url 清空、review_status=rejected）；"
          "需要人工跟进的清单共 %d 行" % (",".join(hit), len(review_rows)))
    return 0


def cmd_manual_urls(args):
    path = args.manual_urls
    if not os.path.isfile(path):
        print("找不到清单文件：%s" % path)
        return 2
    with open(path, newline="", encoding="utf-8-sig") as f:
        # 跳过以 # 开头的注释行（示例文件里有说明性注释）
        lines = [ln for ln in f if not ln.lstrip().startswith("#")]
    reader = csv.DictReader(lines)
    missing = [c for c in MANUAL_COLUMNS if c not in (reader.fieldnames or [])]
    if missing:
        print("清单缺少列：%s" % missing)
        return 2
    entries = [r for r in reader if (r.get("food_id") or "").strip()]

    conn = connect(args)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, name_en, image_url FROM food")
            foods = {str(r["id"]): r for r in cur.fetchall()}
        data = check.collect(conn)
        prev_manifest = {r["food_id"]: r for r in load_csv_rows(MANIFEST_PATH, MANIFEST_COLUMNS)}
        rows = {r["food_id"]: r for r in load_csv_rows(MANIFEST_PATH, MANIFEST_COLUMNS)}
        review_rows = {r["food_id"]: r for r in load_csv_rows(REVIEW_PATH, REVIEW_COLUMNS)}

        jobs, meta = [], {}
        for entry in entries:
            fid = entry["food_id"].strip()
            food = foods.get(fid)
            if not food:
                print("跳过 food_id=%s：库里没有这个食物" % fid)
                continue
            local_path = "/foods/%s-%s.webp" % (fid, slugify(food["name_en"]))
            meta[fid] = dict(food=food, entry=entry, local_path=local_path)
            jobs.append(dict(food_id=fid, download_url=entry["image_url"].strip(),
                             dest_path=os.path.join(FOODS_DIR, os.path.basename(local_path))))

        results = {}
        if jobs:
            print("从清单导入 %d 个 URL，开始下载……" % len(jobs))
            with concurrent.futures.ThreadPoolExecutor(max_workers=DOWNLOAD_WORKERS) as pool:
                for res in pool.map(download_job, jobs):
                    results[res["food_id"]] = res

        for fid, m in meta.items():
            food, entry = m["food"], m["entry"]
            res = results.get(fid, {"status": "failed", "reason": "未执行"})
            if res["status"] == "downloaded":
                attribution = entry.get("attribution") or " / ".join(
                    p for p in [entry.get("photographer"), entry.get("source_name"), entry.get("license")] if p)
                rows[fid] = {
                    "food_id": fid, "food_name": food["name"], "local_path": m["local_path"],
                    "source_name": entry.get("source_name", "manual"), "source_url": entry.get("source_url", ""),
                    "photographer": entry.get("photographer", ""), "license": entry.get("license", ""),
                    "attribution": attribution, "download_status": "downloaded",
                    "review_status": "pending",
                }
                review_rows[fid] = {
                    "food_id": fid, "food_name": food["name"], "search_term": "(manual-urls)",
                    "matched_title": entry.get("source_url", ""), "local_path": m["local_path"],
                    "source_url": entry.get("source_url", ""), "license": entry.get("license", ""),
                }
                print("  ✔ food_id=%s  %.1f KB" % (fid, res["size"] / 1024.0))
            else:
                rows[fid] = _failed_row(food, "(manual-urls)", res["reason"])
                print("  ✘ food_id=%s  %s" % (fid, res["reason"]))

        # 补齐未出现在清单里的食物行（保持 manifest 全量）
        existing_ids = set(rows.keys())
        for fid, food in foods.items():
            if fid in existing_ids:
                continue
            if food["image_url"] and local_decodable(check.map_to_local(food["image_url"])):
                rows[fid] = {"food_id": fid, "food_name": food["name"], "local_path": food["image_url"],
                             "source_name": "existing", "source_url": "", "photographer": "",
                             "license": "unknown", "attribution": "既有资源，来源与许可未记录",
                             "download_status": "existing", "review_status": "approved"}
            else:
                rows[fid] = {"food_id": fid, "food_name": food["name"], "local_path": "",
                             "source_name": "", "source_url": "", "photographer": "", "license": "",
                             "attribution": "未处理：本次未纳入处理范围",
                             "download_status": "missing", "review_status": "n/a"}

        updated = write_db(conn, rows)
        manifest_rows = [rows[k] for k in sorted(rows, key=lambda x: int(x))]
        write_csv(MANIFEST_PATH, MANIFEST_COLUMNS, manifest_rows)
        review_list = build_review_list(manifest_rows, review_rows)
        write_csv(REVIEW_PATH, REVIEW_COLUMNS, review_list)
        print("手动导入完成：写库更新 %d 行，manifest %d 行，待审核 %d 行" % (updated, len(manifest_rows), len(review_list)))
        return 0
    finally:
        conn.close()


# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="食品图片批量补全（搜索/下载/转码/写库）")
    ap.add_argument("--scan", action="store_true", help="只读报告，不下载不写库")
    ap.add_argument("--limit", type=int, default=None, help="只处理前 N 个待补食物")
    ap.add_argument("--provider", choices=["pexels", "pixabay", "commons"], default=None,
                    help="图片提供者；默认按有 Key 优先挑选，都没有用 commons")
    ap.add_argument("--only-food-ids", default=None, help="只处理这些 food_id，逗号分隔")
    ap.add_argument("--manual-urls", default=None, help="从 CSV 清单导入图片 URL（无需 API Key）")
    ap.add_argument("--review", nargs=2, metavar=("FOOD_ID", "STATUS"), default=None,
                    help="更新审核状态：approved | rejected")
    ap.add_argument("--refetch-rejected", action="store_true",
                    help="把 manifest 里 review_status=rejected 的食物强制重取（允许覆盖已有 image_url）")
    ap.add_argument("--clear-image", nargs="+", metavar="FOOD_ID[:原因]", default=None,
                    help="清空这些食物的 image_url 并标 rejected（人工判定找不到合适图）")
    ap.add_argument("--retry-failed", action="store_true", help="只重跑上次失败的食物")
    ap.add_argument("--host", default=DB_DEFAULTS["host"])
    ap.add_argument("--port", type=int, default=DB_DEFAULTS["port"])
    ap.add_argument("--user", default=DB_DEFAULTS["user"])
    ap.add_argument("--password", default=DB_DEFAULTS["password"])
    ap.add_argument("--database", default=DB_DEFAULTS["database"])
    args = ap.parse_args()

    if args.scan:
        return cmd_scan(args)
    if args.manual_urls:
        return cmd_manual_urls(args)
    if args.clear_image:
        return cmd_clear_image(args)
    if args.review:
        return cmd_review(args)
    return run_fetch(args)


if __name__ == "__main__":
    sys.exit(main())