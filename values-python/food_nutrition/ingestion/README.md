# USDA Foundation Foods → MySQL 导入器

把 USDA FoodData Central「Foundation Foods」JSON 里的营养数据导入 `values` 库，
供「食物营养百科」前后端展示。只读源 JSON，不改库表结构，可重复执行。

## 依赖

```powershell
pip install -r values-python/requirements.txt   # 只依赖 pymysql
python --version                                # 需要 Python 3（本机 3.12）
```

## 运行前须知

- 源 JSON 默认路径：`c:\Users\LEGION\Desktop\FoodData_Central_foundation_food_json_2026-04-30.json`
  （6.4 MB，**不放进仓库**）。可用 `--json <路径>` 覆盖。
- 数据库默认连接：`root/123456@localhost:3306/values`，可用
  `--host --port --user --password --database` 覆盖。
- 先在库中执行过 `schema.sql` 与 `data.sql`（`food_category`、`nutrient_info`、
  `data_source` 等字典数据就绪）。

## 四个命令

```powershell
cd values-python/importer

# 1) 体检：只读 JSON、不写库。报告 null 元素数、缺 amount 数、单位清单、
#    目标营养素映射是否齐全、selection.json 的 fdc_id 是否都能对上。
python usda_foundation_importer.py --check

# 2) 演算：内存里算出每个食物保留哪几项，打印将写入的行数与每食物项数分布，不写库。
python usda_foundation_importer.py --dry-run

# 3) 写库：整批放在一个事务里，失败回滚；按 UNIQUE 做 upsert，重复执行不产生重复行。
python usda_foundation_importer.py --apply

# 4) 校验：表计数、每食物项数分布（最大值必须 ≤ 18）、抽 3 个食物逐值比对。
python usda_foundation_importer.py --verify
```

调试时可用 `--limit N` 只处理前 N 条食物。

## mappings/ 各文件职责

| 文件 | 作用 |
| --- | --- |
| `category_map.json` | USDA 分类名 → 本库 `food_category.code` 默认值；`Dairy and Egg Products` 用 description 含 `egg` 关键词覆盖为 EGG。 |
| `provenance_rule.json` | 同一概念多条记录时的取值优先级（按 `nutrient.number` 匹配）：能量 208→957→958→268/4.184、碳水 205→205.2、纤维 291→293、维D 只用 328、维A 只用 320。 |
| `threshold.json` | 丢弃阈值（amount≤0、NRV%<1）、无 NRV 项的绝对下限、每组上限（PROXIMATE 7 / VITAMIN 6 / MINERAL 6 / FATTY_ACID 3）、单食物总量上限 18。 |
| `selection.json` | 要入库的 116 条食物：`fdc_id` / `category_code` / 中文名 / 中文介绍 / 状态。 |

营养素映射**不再单独维护 JSON**：脚本直接读库里的 `nutrient_info.usda_nutrient_id → code`，
所以只有一处来源，新增/调整营养素只需改库。

## 取舍规则

1. `amount` 为空或 ≤0 丢弃；有 NRV 的项若 `NRV% < 1` 丢弃；无 NRV 的项（总糖/水/单不饱和/多不饱和/反式脂肪）按绝对下限丢弃。
2. `nutrient_info.show_in_card=1` 的热量/蛋白质/脂肪/碳水化合物永不丢弃、永不截断。
3. 组内取前 N，总量 ≤ 18（超出时只从维生素/矿物质/脂肪酸里按 NRV% 从低到高截断）。