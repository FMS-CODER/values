# 食品图片批量补全（values-python/food_images）

给 `values` 库里缺图的 `food.image_url` 批量补上图片：搜索 → 初筛 → 下载 → 校验转码 → 写库 → 记录。

## 目录结构

```
food_images/
├── providers.py              # Pexels / Pixabay / Wikimedia Commons 三方搜索（含全局节流与 429 退避）
├── check_food_images.py      # 只读体检脚本：不写库、不下载
├── fetch_food_images.py      # 批量补全主脚本（也提供 --scan / --review / --manual-urls）
├── mappings/
│   ├── keywords.json         # 搜索词覆盖 + 排除词（含覆盖原因）
│   └── manual_urls.example.csv  # 无 API Key 时手工导入图片 URL 的清单格式
└── data/                     # 运行产物（脚本自动生成，可按需删除重跑）
    ├── food-image-manifest.csv     # 全量记录（固定表头）
    ├── review-needed.csv           # 待人工审核清单
    └── rejected-candidates.csv     # 被初筛淘汰的候选及原因
```

## 安装依赖

```powershell
cd values-python
python -m pip install -r requirements.txt   # 没有 python 就用 py -3
```

`requirements.txt` 已含 `pymysql` / `requests` / `Pillow`。

## 命令一览

```powershell
# 只读体检（补全前后各跑一次）
python food_images/check_food_images.py

# 批量补全（默认会按有无 Key 自动挑 provider；都没有就用 commons）
python food_images/fetch_food_images.py

# 只读报告（与 check 脚本等价）
python food_images/fetch_food_images.py --scan

# 只用前 5 个验证链路
python food_images/fetch_food_images.py --provider commons --limit 5

# 只补指定食物 / 只重跑上次失败的
python food_images/fetch_food_images.py --only-food-ids 10,11,12
python food_images/fetch_food_images.py --retry-failed

# 人工审核（approved / rejected）
python food_images/fetch_food_images.py --review 10 approved
python food_images/fetch_food_images.py --review 10 rejected

# 把已判 rejected 的食物按最新搜索词强制重取（会覆盖这两条已写入的 image_url）
python food_images/fetch_food_images.py --provider commons --refetch-rejected

# 确认某个食物找不到合适图：清空 image_url 并标 rejected（前端走占位图兜底）
python food_images/fetch_food_images.py --clear-image 59
python food_images/fetch_food_images.py --clear-image "59:两次换词仍只命中活动现场图"

# 没有 API Key 时：从 CSV 清单导入图片 URL
python food_images/fetch_food_images.py --manual-urls food_images/mappings/my_urls.csv
```

## API Key 怎么设置（只从环境变量读，绝不写进任何文件）

```powershell
# 当前会话临时生效
$env:PEXELS_API_KEY = "你的PexelsKey"
$env:PIXABAY_API_KEY = "你的PixabayKey"

# 想长期生效（用户级，重开终端后仍有效）
[Environment]::SetEnvironmentVariable("PEXELS_API_KEY", "你的PexelsKey", "User")
```

- `--provider pexels|pixabay` 是**显式指定**：若对应环境变量缺失，脚本会**直接报错退出**并提示
  「改用 `--provider commons` 或 `--manual-urls`」，**不会静默降级、更不会伪造成功**。
- 不写 `--provider` 时：有 Pexels Key 用 Pexels，其次 Pixabay，都没有就用 **Wikimedia Commons（无需 Key）**。

### 拿不到 API Key 怎么办

两条都能用：

1. **直接用 Commons**（无需 Key）：`python food_images/fetch_food_images.py --provider commons`
2. **手工清单导入**：把 `mappings/manual_urls.example.csv` 复制成自己的 CSV（例如 `mappings/my_urls.csv`），
   按表头逐行填写后
   `python food_images/fetch_food_images.py --manual-urls food_images/mappings/my_urls.csv`，
   会走完全相同的下载 / 校验 / 转码 / 写库流程。

## 关键设计（每条都说明「为什么」）

- **映射的权威来源是数据库 `food.image_url`**：补全成功后只回写这一列，不维护第二份「食物→图片」表，
  避免两处不一致；且 `UPDATE ... WHERE image_url IS NULL OR image_url=''`，绝不覆盖已有非空值。
- **搜索串行 + 1.2s 节流**：三方搜索 API 会限速，并发搜索只会更快撞 429；下载才用 4 线程（IO 密集、跨站点独立）。
- **文件名 `{food_id}-{slug}.webp`**：`food_id` 稳定、`slug` 由 `name_en` 生成（不用中文），
  重跑时据此判断文件是否已存在，从而做到幂等。
- **缩略图统一进 512×512 等比盒**：卡片 128px、详情页大图 176px，3 倍屏约 528px，512 足够清晰且体积可控；只缩不放。
- **自动匹配一律 `review_status=pending`**：脚本只能做机器初筛，判断不了「图对不对」，最终由人看图确认，绝不自动置 approved。
- **已存在且可解码的本地图片一律跳过**：先写 `.tmp` 再原子重命名，不覆盖、不留半截文件。
  这条默认行为是幂等的基础，**唯一的例外是显式加 `--refetch-rejected`**：只有被人工判为
  `rejected` 的食物才会绕过「已有有效图 / 目标文件已存在」两道跳过并允许覆盖 image_url，
  否则改了搜索词也永远不会重新下载。
- **`rejected` 且已置空的食物会被「按兵不动」**：`--clear-image` 之后 manifest 留下
  `review_status=rejected` + 空 `local_path`，重跑时脚本会跳过它（不检索、不写库、不复活），
  保证「宁可没有图」这个人工结论不会被下一次批量运行推翻。
- **排除词按词边界匹配**：避免 `mango` 命中 `man`、`cantaloupe` 命中 `can` 这类子串误杀。

## 结果文件说明

`data/food-image-manifest.csv`（固定表头，按 `food_id` 排序，每次运行整表重写）：

```
food_id,food_name,local_path,source_name,source_url,photographer,license,attribution,download_status,review_status
```

- `local_path`：前端路径 `/foods/xxx.webp`（与库里的 `image_url` 一致）。
- `download_status` ∈ `existing`（原本就有有效图）/ `downloaded`（本次下载成功）/
  `skipped`（目标文件已存在，跳过下载但仍写库）/ `failed`（本次尝试但失败）/
  `rejected`（人工判定找不到合适图，已置空 image_url）/ `missing`（本次未纳入处理范围）。
- `review_status` ∈ `approved`（人工看过确认可用）/ `pending`（待人工审核）/
  `rejected`（人工判定不合适；若同时 `local_path` 为空表示已置空待人工补图）/ `n/a`（无图可审）。
- 9 条既有图片记为 `existing` + `approved`、`license=unknown`、`attribution=既有资源，来源与许可未记录`，
  **不编造作者与许可**。
- 表头固定，没有单独的原因列：失败原因借用 `attribution` 列承载，形如 `下载失败：<原因>`；
  人工置空的原因同样借用该列，形如 `已置空：<原因>`。

`data/review-needed.csv`：需要人工跟进的条目，列
`food_id,food_name,search_term,matched_title,local_path,source_url,license,reason`。
里面的行是「所有 `pending`」+「所有 `rejected`」：前者等人看图确认，后者等人换图/补图，
`reason` 列写明 rejected 的原因（pending 行为空），供人看图核对。

`data/rejected-candidates.csv`：被初筛淘汰的候选，列
`food_id,food_name,search_term,title,source_name,source_url,reason`。
该文件**累积去重**（按 `food_id+source_url+title+reason` 去重），多次运行不会重复写同一候选，也不会因重跑而膨胀。

## 审核工作流

1. 跑一次补全，自动匹配的图片落在清单里且 `review_status=pending`；
2. 打开 `data/review-needed.csv` 逐张核对图片（看图，不看标题）；
3. 确认可用：`python food_images/fetch_food_images.py --review <food_id> approved`
   （只改审核状态与清单，不动已落盘的图片）；
4. 判定不合适：`--review <food_id> rejected` 标记后，先改 `mappings/keywords.json` 里该
   food_id 的 `search_term`（必要时加 `extra_exclude_words`），再
   `python food_images/fetch_food_images.py --provider commons --refetch-rejected` 重取，
   然后回到第 2 步重新看图；
5. 换了两次搜索词仍只能拿到不相关的图：**不要再凑合**，用
   `--clear-image "<food_id>:<原因>"` 置空（错误图比没有图更差），结论会写进
   review-needed 的 `reason` 列；
6. 修完重复跑一次不带参数的 `fetch_food_images.py`，应当显示「本次需处理 0」——
   既不重复下载、也不覆盖人工结论，manifest 与 review-needed 保持与最新审核状态一致。