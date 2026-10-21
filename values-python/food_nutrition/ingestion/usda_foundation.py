#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""USDA FoodData Central「Foundation Foods」→ MySQL(values 库) 营养数据导入脚本。

用法（四个阶段，互斥）：
    python -m food_nutrition ingest --check      # 只读 JSON 不写库，体检数据
    python -m food_nutrition ingest --dry-run    # 内存里演算，打印将写入的行数，不写库
    python -m food_nutrition ingest --apply      # 单事务写库
    python -m food_nutrition ingest --verify     # 写库后校验，逐值比对

也可以直接跑本模块：
    python -m food_nutrition.ingestion.usda_foundation --check

可选参数：
    --json <路径>   指定源 JSON（默认取环境变量 USDA_JSON_PATH，或桌面上的样例文件）
    --limit N       只处理 selection.json 里的前 N 条，便于快速调试
    --host/--port/--user/--password/--database  覆盖数据库连接默认值
"""

import argparse
import json
import os
import statistics
import sys
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

import pymysql

from ..config import DEFAULT_USDA_JSON, INGESTION_MAPPINGS_DIR, db_config

# Windows 控制台默认可能是 GBK，源数据和营养素里含 µ 等字符，统一切到 UTF-8 输出。
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# 映射表随包分发；路径统一由 config 推导，避免脚本移动后相对路径失效
MAPPINGS_DIR = str(INGESTION_MAPPINGS_DIR)
DEFAULT_JSON = str(DEFAULT_USDA_JSON)

DB_DEFAULTS = db_config()

# nutrient_info 里没规定 NRV 的项用绝对下限判定（单位 g/100g）。
GROUP_ORDER = ["PROXIMATE", "VITAMIN", "MINERAL", "FATTY_ACID"]


# --------------------------------------------------------------------------
# 配置装载
# --------------------------------------------------------------------------
def load_mappings():
    def _load(name):
        with open(os.path.join(MAPPINGS_DIR, name), encoding="utf-8") as f:
            return json.load(f)

    return {
        "category_map": _load("category_map.json"),
        "provenance_rule": _load("provenance_rule.json"),
        "threshold": _load("threshold.json"),
        "selection": _load("selection.json"),
    }


def resolve_category(category_map, usda_category, description):
    """按 USDA 分类给默认值，再用 description 关键词覆盖。"""
    desc = (description or "").lower()
    for rule in category_map.get("keyword_overrides", []):
        if rule.get("scope_category") == usda_category and rule.get("pattern", "").lower() in desc:
            return rule["to"]
    return category_map.get("default_by_category", {}).get(
        usda_category, category_map.get("fallback", "OTHER")
    )


def parse_usda_date(value):
    """USDA 的 publicationDate 是 M/D/YYYY（个位数月/日不带前导零），要转成 YYYY-MM-DD。"""
    if not value:
        return None
    for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


# --------------------------------------------------------------------------
# JSON 装载
# --------------------------------------------------------------------------
def load_foods(path):
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    all_items = raw["FoundationFoods"]
    # 顶层数组里有若干 null 元素（该数据集已知问题），必须先过滤，否则后面取字段会炸。
    foods = [x for x in all_items if x]
    return all_items, foods


def index_nutrients(food):
    """把一个食物的 foodNutrients 拆成按 nutrient.number 和 nutrient.id 两张索引。

    amount 一律用 Decimal(str(x)) 转换：JSON 里是浮点数，直接 float 运算会有二进制误差，
    而后续要做除法（kJ→kcal）与阈值比较，必须用精确十进制。
    """
    by_number, by_id = {}, {}
    for n in food.get("foodNutrients", []):
        nt = n.get("nutrient") or {}
        amt = n.get("amount")
        rec = {
            "amount": None if amt is None else Decimal(str(amt)),
            "unit": nt.get("unitName"),
            "data_points": n.get("dataPoints"),
            "derivation": (n.get("foodNutrientDerivation") or n.get("derivation") or {}).get("code"),
            "number": str(nt.get("number")),
        }
        by_number[rec["number"]] = rec
        if nt.get("id") is not None:
            by_id[int(nt["id"])] = rec
    return by_number, by_id


# --------------------------------------------------------------------------
# 核心：计算一个食物最终保留的营养素
# --------------------------------------------------------------------------
def quantize_amount(amount, unit):
    """按单位保留合理小数：g / mg / µg 保留 2 位，kcal 保留 0 位。"""
    q = Decimal("1") if unit == "kcal" else Decimal("0.01")
    return amount.quantize(q, rounding=ROUND_HALF_UP)


def compute_food_nutrients(food, meta, prov_rules, thr):
    """返回 (kept, decisions)。kept 为最终入库项，decisions 为逐项取舍说明。"""
    by_number, by_id = index_nutrients(food)
    nrv_min = Decimal(str(thr["nrv_percent_min"]))
    abs_min = thr.get("absolute_min", {})

    kept, decisions = [], []
    for ni in meta:
        code = ni["code"]
        group = ni["nutrient_group"]

        # 1) 取原始数值：先看是否有「同概念优先级」规则，否则按 usda_nutrient_id 精确匹配
        rule = prov_rules.get(code)
        got = None
        used_number = None
        if rule:
            for num in rule["numbers"]:
                rec = by_number.get(num)
                if rec and rec["amount"] is not None:
                    got, used_number = rec, num
                    break
            if got is not None:
                divisor = (rule.get("divide_by") or {}).get(used_number)
                if divisor:  # 例如 268 是 kJ，要 /4.184 换成 kcal 口径
                    got = dict(got, amount=got["amount"] / Decimal(str(divisor)))
        else:
            got = by_id.get(ni["usda_nutrient_id"])
            used_number = got["number"] if got else None

        if got is None or got["amount"] is None:
            decisions.append((code, "无数据", None))
            continue

        amount = got["amount"]
        show = bool(ni["show_in_card"])
        nrv_value = ni["nrv_value"]
        nrv_pct = None
        if nrv_value is not None:
            conv = ni["nrv_conversion_factor"] or Decimal("1")
            nrv_pct = amount * conv / Decimal(str(nrv_value)) * 100

        # 2) 过滤
        if amount <= 0 and not show:
            decisions.append((code, "amount≤0", None))
            continue
        if not show and nrv_value is not None:
            if nrv_pct < nrv_min:
                decisions.append((code, "NRV%%<%.0f" % thr["nrv_percent_min"], nrv_pct))
                continue
        elif not show and nrv_value is None:
            floor = abs_min.get(code)
            if floor is not None and amount < Decimal(str(floor)):
                decisions.append((code, "低于绝对下限%s" % floor, None))
                continue

        kept.append({
            "code": code,
            "group": group,
            "unit": ni["unit"],
            "amount": amount,
            "nrv_pct": nrv_pct,
            "show_in_card": show,
            "sort_order": ni["sort_order"],
            "data_points": got["data_points"],
            "derivation": got["derivation"],
            "used_number": used_number,
        })

    # 3) 组内上限：VITAMIN/MINERAL 按 NRV% 降序取前 N（无 NRV 排最后），FATTY_ACID 同理
    def group_key(it):
        nrv = it["nrv_pct"]
        return (0 if nrv is not None else 1, -(nrv if nrv is not None else Decimal(0)), it["sort_order"])

    caps = thr["group_caps"]
    result = []
    for group in GROUP_ORDER:
        items = [x for x in kept if x["group"] == group]
        cap = caps.get(group)
        if cap is not None and len(items) > cap:
            items.sort(key=group_key)
            for extra in items[cap:]:
                decisions.append((extra["code"], "超出组上限%s" % cap, extra["nrv_pct"]))
            items = items[:cap]
        result.extend(items)

    # 4) 总量上限：超过 18 时，只从 VITAMIN/MINERAL/FATTY_ACID 里按 NRV% 从低到高砍
    total_cap = thr["total_cap"]
    while len(result) > total_cap:
        removable = [x for x in result
                     if not x["show_in_card"] and x["group"] in ("VITAMIN", "MINERAL", "FATTY_ACID")]
        if not removable:
            break
        removable.sort(key=lambda it: (
            1 if it["nrv_pct"] is not None else 0,
            it["nrv_pct"] if it["nrv_pct"] is not None else Decimal(0),
        ))
        victim = removable[0]
        result.remove(victim)
        decisions.append((victim["code"], "总量>%d 截断" % total_cap, victim["nrv_pct"]))

    result.sort(key=lambda it: (GROUP_ORDER.index(it["group"]), it["sort_order"]))
    return result, decisions


# --------------------------------------------------------------------------
# 数据库读取
# --------------------------------------------------------------------------
def connect(args):
    return pymysql.connect(
        host=args.host, port=args.port, user=args.user, password=args.password,
        database=args.database, charset="utf8mb4", autocommit=False,
        cursorclass=pymysql.cursors.DictCursor,
    )


def load_meta(conn):
    """营养素映射的唯一来源：直接读库里的 nutrient_info，不再维护第二份 JSON。"""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT code, name_en, unit, nutrient_group, usda_nutrient_id, usda_number, "
            "nrv_value, nrv_conversion_factor, show_in_card, sort_order FROM nutrient_info"
        )
        meta = cur.fetchall()
    for m in meta:
        m["sort_order"] = int(m["sort_order"])
        m["show_in_card"] = int(m["show_in_card"])
        if m["usda_nutrient_id"] is not None:
            m["usda_nutrient_id"] = int(m["usda_nutrient_id"])
    meta.sort(key=lambda m: (GROUP_ORDER.index(m["nutrient_group"]), m["sort_order"]))
    return meta


def get_source_id(conn):
    """查 USDA_FOUNDATION 的来源 id，不硬编码。"""
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM data_source WHERE code=%s", ("USDA_FOUNDATION",))
        row = cur.fetchone()
    if not row:
        raise RuntimeError("data_source 中找不到 code='USDA_FOUNDATION'")
    return int(row["id"])


def get_category_ids(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT id, code FROM food_category")
        return {r["code"]: int(r["id"]) for r in cur.fetchall()}


# --------------------------------------------------------------------------
# 组装待写入数据
# --------------------------------------------------------------------------
def build_plan(foods_by_id, selection, meta, prov_rules, thr, category_map, category_ids,
               source_id, limit=None):
    """返回 (plan, missing_selection)。plan 每项含食物行与营养素行（尚未写库）。"""
    subsets = selection[:limit] if limit else selection
    plan, missing = [], []
    for sel in subsets:
        fdc = int(sel["fdc_id"])
        food = foods_by_id.get(fdc)
        if food is None:
            missing.append(fdc)
            continue

        usda_category = (food.get("foodCategory") or {}).get("description")
        mapped = resolve_category(category_map, usda_category, food.get("description"))
        # selection.json 的分类是人工校订过的（例如大蒜/洋葱归香辛料），优先采用；
        # 缺省时才回落到 category_map 的默认/关键词结果。
        code = sel.get("category_code") or mapped
        category_id = category_ids.get(code)
        if category_id is None:
            raise RuntimeError("分类 code=%s 在 food_category 中不存在" % code)

        kept, decisions = compute_food_nutrients(food, meta, prov_rules, thr)
        nutrients = [{
            "nutrient_code": it["code"],
            "amount": quantize_amount(it["amount"], it["unit"]),
            "data_points": it["data_points"],
            "derivation_code": it["derivation"],
        } for it in kept]

        plan.append({
            "fdc_id": fdc,
            "food_row": {
                "name": sel.get("name_zh") or food.get("description"),
                "name_en": food.get("description"),
                "category_id": category_id,
                "description": sel.get("description") or None,
                "state": sel.get("state") or None,
                "fdc_id": fdc,
                "ndb_number": None if food.get("ndbNumber") in (None, "") else str(food["ndbNumber"]),
                "data_type": food.get("dataType"),
                "publication_date": parse_usda_date(food.get("publicationDate")),
                "source_id": source_id,
                "source_record_id": str(fdc),
                "source_note": "USDA FoodData Central · Foundation Foods，FDC ID %d。" % fdc,
            },
            "nutrients": nutrients,
            "decisions": decisions,
            "category_code": code,
            "category_map_code": mapped,
            "usda_description": food.get("description"),
        })
    return plan, missing


# --------------------------------------------------------------------------
# 各命令
# --------------------------------------------------------------------------
def cmd_check(args):
    all_items, foods = load_foods(args.json)
    maps = load_mappings()
    meta = None
    conn = None
    try:
        conn = connect(args)
        meta = load_meta(conn)
        source_id = get_source_id(conn)
    finally:
        if conn:
            conn.close()

    print("=" * 72)
    print("① 源文件体检：%s" % args.json)
    print("=" * 72)
    print("顶层数组元素总数 : %d" % len(all_items))
    print("其中 null 元素     : %d（已过滤，不参与导入）" % (len(all_items) - len(foods)))
    print("有效食物条目       : %d" % len(foods))

    total_fn = missing_amount = 0
    units = {}
    numbers_in_json = set()
    for f in foods:
        for n in f.get("foodNutrients", []):
            total_fn += 1
            nt = n.get("nutrient") or {}
            numbers_in_json.add(str(nt.get("number")))
            if n.get("amount") is None:
                missing_amount += 1
            else:
                u = nt.get("unitName")
                units[u] = units.get(u, 0) + 1
    print("foodNutrients 总条数: %d，其中 amount 为空: %d" % (total_fn, missing_amount))
    print("出现的单位清单      : %s" % ", ".join("%s(%d)" % (k, v) for k, v in sorted(units.items(), key=lambda x: -x[1])))

    print()
    print("-" * 72)
    print("② 目标营养素映射检查（只可能入库 nutrient_info 这 %d 项）" % len(meta))
    print("-" * 72)
    prov = maps["provenance_rule"]["rules"]
    # 目标编号 = nutrient_info 里登记的 usda_number ∪ provenance 里的备用编号
    target_numbers = set()
    for m in meta:
        if m["usda_number"]:
            target_numbers.add(str(m["usda_number"]).strip())
    for rule in prov.values():
        target_numbers.update(rule["numbers"])

    mapped_ids = [m for m in meta if m["usda_nutrient_id"] is not None]
    # 收集 JSON 中所有 nutrient.id
    ids_in_json = set()
    for f in foods:
        for n in f.get("foodNutrients", []):
            nid = (n.get("nutrient") or {}).get("id")
            if nid is not None:
                ids_in_json.add(int(nid))
    ids_missing = [m["code"] for m in mapped_ids if m["usda_nutrient_id"] not in ids_in_json]
    print("nutrient_info 登记 id 数: %d；其中 JSON 中未出现: %d %s"
          % (len(mapped_ids), len(ids_missing), ids_missing or ""))

    target_in_json = sorted(n for n in target_numbers if n in numbers_in_json)
    print("目标营养素编号（35 项 number ∪ 优先级备用号）: %d 个" % len(target_numbers))
    print("其中 JSON 中出现的: %d 个 -> %s" % (len(target_in_json), target_in_json))

    # 「JSON 里有、但 nutrient_info.usda_nutrient_id 没有」的目标项：
    # 目标项若不在 nutrient_info 的 id 集合里，必须能被 provenance 规则解释，否则就是漏配。
    id_numbers = {str(m["usda_number"]).strip() for m in mapped_ids if m["usda_number"]}
    prov_numbers = set()
    for rule in prov.values():
        prov_numbers.update(rule["numbers"])
    unresolved = [n for n in target_in_json if n not in id_numbers and n not in prov_numbers]
    print("JSON 里有、但既无 nutrient_info.usda_nutrient_id、也不在优先级规则里的目标项: %d %s"
          % (len(unresolved), unresolved or "→ 通过"))
    print("仅供对照：JSON 里的营养编号共 %d 种，其余（氨基酸/甾醇/类胡萝卜素/逐碳链脂肪酸等）按设计忽略。"
          % len(numbers_in_json))

    print()
    print("-" * 72)
    print("③ selection.json 校验")
    print("-" * 72)
    print("待入库食物条目: %d" % len(maps["selection"]))
    foods_by_id = {int(f["fdcId"]): f for f in foods}
    bad = [s["fdc_id"] for s in maps["selection"] if int(s["fdc_id"]) not in foods_by_id]
    print("对不上 fdc_id 的条目: %d %s" % (len(bad), bad or "→ 全部匹配"))

    # 顺带展示 category_map 与 selection 分类不一致的条目（说明覆盖机制在生效）
    mismatched = []
    for s in maps["selection"]:
        f = foods_by_id.get(int(s["fdc_id"]))
        if not f:
            continue
        uc = (f.get("foodCategory") or {}).get("description")
        mapped = resolve_category(maps["category_map"], uc, f.get("description"))
        if mapped != s["category_code"]:
            mismatched.append((s["fdc_id"], s["name_zh"], mapped, s["category_code"]))
    print("selection 分类覆盖 category_map 的条目: %d 条（人工校订优先）" % len(mismatched))
    for fdc, zh, mapped, chosen in mismatched:
        print("    %-9s %-6s category_map=%s -> selection=%s" % (fdc, zh, mapped, chosen))
    print("（USDA_FOUNDATION source_id = %d）" % source_id)


def cmd_dry_run(args):
    all_items, foods = load_foods(args.json)
    maps = load_mappings()
    conn = connect(args)
    try:
        meta = load_meta(conn)
        source_id = get_source_id(conn)
        category_ids = get_category_ids(conn)
    finally:
        conn.close()

    foods_by_id = {int(f["fdcId"]): f for f in foods}
    plan, missing = build_plan(foods_by_id, maps["selection"], meta,
                               maps["provenance_rule"]["rules"], maps["threshold"],
                               maps["category_map"], category_ids, source_id, args.limit)

    print("=" * 72)
    print("DRY-RUN：只演算、不写库（limit=%s）" % (args.limit or "无"))
    print("=" * 72)
    counts = [len(p["nutrients"]) for p in plan]
    total_nutrients = sum(counts)
    print("将处理食物        : %d 条（selection 未匹配: %d）" % (len(plan), len(missing)))
    print("预计写入 food     : 新增 %d 条（其余 fdc_id 已存在，只补营养值）"
          % sum(1 for p in plan if p["fdc_id"] not in _existing_fdc_ids))
    print("预计写入 food_nutrient: %d 行" % total_nutrients)
    print("每食物项数分布    : min=%d 中位=%.0f max=%d" % (min(counts), statistics.median(counts), max(counts)))
    dist = {}
    for c in counts:
        dist[c] = dist.get(c, 0) + 1
    print("项数直方图        : %s" % ", ".join("%d项×%d" % (k, dist[k]) for k in sorted(dist)))
    if max(counts) > 18:
        print("!! 存在 >18 项的食物: %s" % [p["fdc_id"] for p in plan if len(p["nutrients"]) > 18])
    else:
        print("全部食物项数 ≤ 18 ✔")

    # 抽样说明：挑几个食物展示被丢弃/截断的原因
    print()
    print("-" * 72)
    print("取舍抽样说明（前 4 个食物 + 丢弃最多的 1 个）")
    print("-" * 72)
    sample = plan[:4]
    worst = max(plan, key=lambda p: len(p["decisions"]))
    if worst not in sample:
        sample.append(worst)
    for p in sample:
        kept = [n["nutrient_code"] for n in p["nutrients"]]
        print("[%s] %s (%s) 保留 %d 项: %s"
              % (p["fdc_id"], p["food_row"]["name"], p["category_code"], len(kept), ",".join(kept)))
        for code, reason, pct in p["decisions"][:8]:
            extra = "" if pct is None else " NRV%%=%.1f" % pct
            print("      丢弃 %-20s 原因: %s%s" % (code, reason, extra))


def cmd_apply(args):
    maps = load_mappings()
    all_items, foods = load_foods(args.json)
    foods_by_id = {int(f["fdcId"]): f for f in foods}
    conn = connect(args)
    try:
        meta = load_meta(conn)
        source_id = get_source_id(conn)
        category_ids = get_category_ids(conn)
        plan, missing = build_plan(foods_by_id, maps["selection"], meta,
                                   maps["provenance_rule"]["rules"], maps["threshold"],
                                   maps["category_map"], category_ids, source_id, args.limit)
        if missing:
            print("警告：selection 里以下 fdc_id 未匹配到 JSON，跳过：%s" % missing)

        existing = _existing_fdc_ids
        inserted_food = updated_food = 0
        nutrient_rows = 0
        try:
            with conn.cursor() as cur:
                for p in plan:
                    fdc = p["fdc_id"]
                    row = p["food_row"]
                    if fdc in existing:
                        # 已存在的食物（含预置的 9 条）只补营养值，绝不动名称/图片/介绍/状态/claim_note
                        food_id = existing[fdc]
                    else:
                        cur.execute(
                            "INSERT INTO food (name,name_en,category_id,image_url,description,state,"
                            "fdc_id,ndb_number,data_type,publication_date,source_id,source_record_id,"
                            "verified,source_note,claim_note) "
                            "VALUES (%s,%s,%s,NULL,%s,%s,%s,%s,%s,%s,%s,%s,1,%s,NULL) "
                            "ON DUPLICATE KEY UPDATE id=LAST_INSERT_ID(id)",
                            (row["name"], row["name_en"], row["category_id"], row["description"],
                             row["state"], row["fdc_id"], row["ndb_number"], row["data_type"],
                             row["publication_date"], row["source_id"], row["source_record_id"],
                             row["source_note"]),
                        )
                        food_id = cur.lastrowid
                        inserted_food += 1

                    for n in p["nutrients"]:
                        cur.execute(
                            "INSERT INTO food_nutrient (food_id,nutrient_code,amount,basis_type,"
                            "basis_amount,edible_portion,data_points,derivation_code,source_id,"
                            "source_record_id) VALUES (%s,%s,%s,'100G',100,1,%s,%s,%s,%s) "
                            "ON DUPLICATE KEY UPDATE amount=VALUES(amount),"
                            "data_points=VALUES(data_points), derivation_code=VALUES(derivation_code),"
                            "source_id=VALUES(source_id), source_record_id=VALUES(source_record_id)",
                            (food_id, n["nutrient_code"], n["amount"], n["data_points"],
                             n["derivation_code"], source_id, str(fdc)),
                        )
                        nutrient_rows += 1
            conn.commit()
        except Exception:
            conn.rollback()  # 整批一个事务，失败必须回滚，不留半截数据
            raise
        print("=" * 72)
        print("APPLY 完成（单事务已提交）")
        print("=" * 72)
        print("food: 新增 %d 条 / 复用已存在 %d 条" % (inserted_food, len(plan) - inserted_food))
        print("food_nutrient: 处理 %d 行（重复执行会被 UNIQUE 去重，不产生重复行）" % nutrient_rows)
    finally:
        conn.close()


def cmd_verify(args):
    maps = load_mappings()
    all_items, foods = load_foods(args.json)
    foods_by_id = {int(f["fdcId"]): f for f in foods}
    conn = connect(args)
    try:
        meta = load_meta(conn)
        source_id = get_source_id(conn)
        category_ids = get_category_ids(conn)
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) c FROM food")
            food_cnt = cur.fetchone()["c"]
            cur.execute("SELECT COUNT(*) c FROM food_nutrient")
            fn_cnt = cur.fetchone()["c"]
            cur.execute("SELECT COUNT(*) c FROM food_category")
            cat_cnt = cur.fetchone()["c"]
            cur.execute("SELECT COUNT(*) c FROM nutrient_info")
            ni_cnt = cur.fetchone()["c"]
            cur.execute("SELECT food_id, COUNT(*) c FROM food_nutrient GROUP BY food_id")
            per_food = [r["c"] for r in cur.fetchall()]
            cur.execute("SELECT food_id, COUNT(*) c FROM food_nutrient GROUP BY food_id HAVING c > 18")
            over = cur.fetchall()

        print("=" * 72)
        print("VERIFY：写库结果核对")
        print("=" * 72)
        print("表计数  ：food=%d  food_nutrient=%d  food_category=%d  nutrient_info=%d"
              % (food_cnt, fn_cnt, cat_cnt, ni_cnt))
        if per_food:
            print("每食物项数分布：min=%d 中位=%.0f max=%d（覆盖 %d 个食物）"
                  % (min(per_food), statistics.median(per_food), max(per_food), len(per_food)))
        else:
            print("food_nutrient 为空")
        print("count>18 的食物：%s" % (over if over else "空 ✔（符合上限要求）"))

        # 逐值比对：抽 3 个食物，把库里的数值与源 JSON 重新演算的结果逐项对照
        print()
        print("-" * 72)
        print("逐值比对（库内值 vs 源 JSON 重算值）")
        print("-" * 72)
        picks = [747447, 2646170, 2346393]
        with conn.cursor() as cur:
            for fdc in picks:
                food = foods_by_id.get(fdc)
                cur.execute("SELECT id, name FROM food WHERE fdc_id=%s", (fdc,))
                frow = cur.fetchone()
                if not food or not frow:
                    print("[%s] 缺失，跳过" % fdc)
                    continue
                recomputed = {it["code"]: quantize_amount(it["amount"], it["unit"])
                              for it in compute_food_nutrients(
                                  food, meta, maps["provenance_rule"]["rules"], maps["threshold"])[0]}
                cur.execute(
                    "SELECT nutrient_code, amount, data_points, derivation_code, basis_type "
                    "FROM food_nutrient WHERE food_id=%s ORDER BY nutrient_code", (frow["id"],))
                rows = cur.fetchall()
                print("[%s] %s 库内 %d 项" % (fdc, frow["name"], len(rows)))
                all_ok = True
                for r in rows:
                    src = recomputed.get(r["nutrient_code"])
                    ok = (src is not None and Decimal(str(r["amount"])) == src)
                    all_ok = all_ok and ok
                    print("    %-20s 库=%-12s 源=%-12s 单位基准=%s dataPoints=%s deriv=%s %s"
                          % (r["nutrient_code"], r["amount"], src, r["basis_type"],
                             r["data_points"], r["derivation_code"], "✔" if ok else "✘不一致"))
                print("    → 全部一致 ✔" if all_ok else "    → 存在不一致 ✘")
    finally:
        conn.close()


def _load_existing(conn, fdc_ids):
    """查库中已存在这些 fdc_id 的 food 行，返回 {fdc_id: food_id}。"""
    out = {}
    if not fdc_ids:
        return out
    with conn.cursor() as cur:
        fmt = ",".join(["%s"] * len(fdc_ids))
        cur.execute("SELECT id, fdc_id FROM food WHERE fdc_id IN (%s)" % fmt, tuple(fdc_ids))
        for r in cur.fetchall():
            out[int(r["fdc_id"])] = int(r["id"])
    return out


_existing_fdc_ids = {}


def main():
    global _existing_fdc_ids
    ap = argparse.ArgumentParser(description="USDA Foundation Foods → MySQL 导入")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true", help="只读 JSON 不写库，体检")
    g.add_argument("--dry-run", action="store_true", help="内存演算，不写库")
    g.add_argument("--apply", action="store_true", help="单事务写库")
    g.add_argument("--verify", action="store_true", help="写库后校验")
    ap.add_argument("--json", default=DEFAULT_JSON, help="源 JSON 路径")
    ap.add_argument("--limit", type=int, default=None, help="只处理前 N 条")
    ap.add_argument("--host", default=DB_DEFAULTS["host"])
    ap.add_argument("--port", type=int, default=DB_DEFAULTS["port"])
    ap.add_argument("--user", default=DB_DEFAULTS["user"])
    ap.add_argument("--password", default=DB_DEFAULTS["password"])
    ap.add_argument("--database", default=DB_DEFAULTS["database"])
    args = ap.parse_args()

    # 先把已存在的 fdc_id 查出来（--dry-run 也要用）
    conn = connect(args)
    try:
        maps = load_mappings()
        fdc_ids = [int(s["fdc_id"]) for s in maps["selection"]]
        _existing_fdc_ids = _load_existing(conn, fdc_ids)
    finally:
        conn.close()

    if args.check:
        cmd_check(args)
    elif args.dry_run:
        cmd_dry_run(args)
    elif args.apply:
        cmd_apply(args)
    elif args.verify:
        cmd_verify(args)


if __name__ == "__main__":
    main()