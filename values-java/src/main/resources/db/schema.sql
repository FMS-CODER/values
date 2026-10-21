-- 食物营养百科 · 库表结构
-- 执行方式（PowerShell）：
--   & "D:\mysql\MySQL Server 8.0\bin\mysql.exe" -uroot -p --default-character-set=utf8mb4 -e "source <本文件绝对路径>"
-- 设计要点：
--   1. 营养数值统一按「每 100g 可食部分」存储，单位只保存在 nutrient_info，避免两处不一致；
--   2. 「富含」判定规则字段化（rich_rule_type + 阈值 + 依据），新增营养素不需要改 Java 代码；
--   3. 来源链接不建字段，只有科普内容需要逐条引用来源，故保留 nutrient_knowledge.source_url。

CREATE DATABASE IF NOT EXISTS `values`
  DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;

USE `values`;

-- ---------------------------------------------------------------- 字典表

-- 食物分类字典。「全部」是前端筛选状态，不入库
CREATE TABLE IF NOT EXISTS food_category (
  id         TINYINT UNSIGNED NOT NULL,
  code       VARCHAR(32) NOT NULL COMMENT '稳定编码，如 VEGETABLE',
  name       VARCHAR(32) NOT NULL COMMENT '中文名，即筛选按钮文案',
  sort_order SMALLINT    NOT NULL DEFAULT 0 COMMENT '筛选按钮顺序',
  PRIMARY KEY (id),
  UNIQUE KEY uk_food_category_code (code),
  UNIQUE KEY uk_food_category_name (name)
) ENGINE=InnoDB COMMENT='食物分类字典';

-- 营养数据来源字典。只记名称，来源链接由前端常量维护
CREATE TABLE IF NOT EXISTS data_source (
  id   SMALLINT UNSIGNED NOT NULL AUTO_INCREMENT,
  code VARCHAR(32) NOT NULL COMMENT 'USDA_SR_LEGACY / DEMO',
  name VARCHAR(64) NOT NULL COMMENT '页面「数据来源」文案',
  PRIMARY KEY (id),
  UNIQUE KEY uk_data_source_code (code)
) ENGINE=InnoDB COMMENT='营养数据来源字典';

-- 营养声称判定依据的标准字典
CREATE TABLE IF NOT EXISTS rule_source (
  id             SMALLINT UNSIGNED NOT NULL AUTO_INCREMENT,
  code           VARCHAR(32)  NOT NULL COMMENT 'GB_28050_2025',
  name           VARCHAR(64)  NOT NULL COMMENT '页面展示的标准名',
  effective_date DATE         NULL COMMENT '实施日期',
  scope_note     VARCHAR(255) NULL COMMENT '适用范围说明',
  PRIMARY KEY (id),
  UNIQUE KEY uk_rule_source_code (code)
) ENGINE=InnoDB COMMENT='营养声称判定依据的标准字典';

-- ---------------------------------------------------------- 营养素与规则

-- 营养素基础表 + 富含判定规则
CREATE TABLE IF NOT EXISTS nutrient_info (
  code                    VARCHAR(32)   NOT NULL COMMENT '稳定编码，如 VITAMIN_C',
  name                    VARCHAR(32)   NOT NULL COMMENT '中文名称',
  unit                    VARCHAR(8)    NOT NULL COMMENT '含量单位 mg/g/kcal',
  nutrient_group          VARCHAR(16)   NOT NULL COMMENT 'VITAMIN/MINERAL/PROTEIN/FIBER/OTHER',
  nrv_value               DECIMAL(12,3) NULL COMMENT '营养素参考值，未规定则为空',
  nrv_unit                VARCHAR(8)    NULL COMMENT 'NRV 的单位，可能与 unit 不同',
  nrv_conversion_factor   DECIMAL(12,6) NULL COMMENT '含量换算到 nrv_unit 的系数，能量为 4.184',
  rich_rule_type          VARCHAR(16)   NOT NULL DEFAULT 'NONE' COMMENT 'NRV_PERCENT/ABSOLUTE/NONE',
  rich_threshold_percent  DECIMAL(5,2)  NULL COMMENT 'NRV_PERCENT 阈值，如 30 表示 ≥30% NRV',
  rich_threshold_per_100g DECIMAL(12,3) NULL COMMENT 'ABSOLUTE 阈值，如 12 表示 ≥12g/100g',
  rule_source_id          SMALLINT UNSIGNED NULL COMMENT '判定依据来源',
  rule_note               VARCHAR(255)  NULL COMMENT '判定依据文字说明',
  show_in_card            TINYINT(1)    NOT NULL DEFAULT 0 COMMENT '1=出现在列表卡片',
  sort_order              SMALLINT      NOT NULL DEFAULT 0 COMMENT '详情页展示顺序',
  PRIMARY KEY (code),
  KEY idx_nutrient_rule_source (rule_source_id),
  CONSTRAINT fk_nutrient_rule_source FOREIGN KEY (rule_source_id) REFERENCES rule_source (id)
) ENGINE=InnoDB COMMENT='营养素基础表（含富含判定规则）';

-- 营养素科普内容与来源。与 nutrient_info 一一对应
CREATE TABLE IF NOT EXISTS nutrient_knowledge (
  nutrient_code VARCHAR(32)  NOT NULL,
  role          VARCHAR(255) NOT NULL COMMENT '生理作用',
  source_name   VARCHAR(64)  NOT NULL COMMENT 'MedlinePlus / NIH ODS',
  source_url    VARCHAR(255) NULL COMMENT '科普内容来源网址',
  verified_at   DATE         NULL COMMENT '最近一次核对来源内容的日期',
  PRIMARY KEY (nutrient_code),
  CONSTRAINT fk_knowledge_nutrient FOREIGN KEY (nutrient_code) REFERENCES nutrient_info (code)
) ENGINE=InnoDB COMMENT='营养素科普内容与来源';

-- ---------------------------------------------------------- 食物与含量

CREATE TABLE IF NOT EXISTS food (
  id               BIGINT UNSIGNED   NOT NULL AUTO_INCREMENT,
  name             VARCHAR(64)       NOT NULL COMMENT '食物名称',
  category_id      TINYINT UNSIGNED  NOT NULL COMMENT '所属分类',
  image_url        VARCHAR(255)      NOT NULL COMMENT '食物图片地址',
  description      VARCHAR(255)      NOT NULL COMMENT '一句话介绍',
  state            VARCHAR(32)       NOT NULL COMMENT '食品状态，如「生，带皮」',
  source_id        SMALLINT UNSIGNED NOT NULL COMMENT '数据来源',
  source_record_id VARCHAR(64)       NULL COMMENT '来源记录 ID，如 FDC 171688',
  verified         TINYINT(1)        NOT NULL DEFAULT 0 COMMENT '0=页面显示「待校验」',
  source_note      VARCHAR(255)      NULL COMMENT '该食物的核验或使用说明',
  claim_note       VARCHAR(255)      NULL COMMENT '需要单独说明的营养声称提示',
  created_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_food_category (category_id),
  KEY idx_food_name (name),
  CONSTRAINT fk_food_category FOREIGN KEY (category_id) REFERENCES food_category (id),
  CONSTRAINT fk_food_source   FOREIGN KEY (source_id)   REFERENCES data_source (id)
) ENGINE=InnoDB COMMENT='食物基础表';

-- 食物营养成分表。单位不重复保存，取 nutrient_info.unit
CREATE TABLE IF NOT EXISTS food_nutrient (
  id               BIGINT UNSIGNED   NOT NULL AUTO_INCREMENT,
  food_id          BIGINT UNSIGNED   NOT NULL,
  nutrient_code    VARCHAR(32)       NOT NULL,
  amount           DECIMAL(12,4)     NOT NULL COMMENT '实际含量',
  basis_type       VARCHAR(16)       NOT NULL DEFAULT '100G' COMMENT '100G/100ML/PER_SERVING',
  basis_amount     DECIMAL(8,2)      NOT NULL DEFAULT 100 COMMENT '计量基准数量',
  edible_portion   TINYINT(1)        NOT NULL DEFAULT 1 COMMENT '1=按可食部分计',
  source_id        SMALLINT UNSIGNED NULL COMMENT '该条数值的来源',
  source_record_id VARCHAR(64)       NULL COMMENT '来源记录 ID',
  PRIMARY KEY (id),
  UNIQUE KEY uk_food_nutrient (food_id, nutrient_code, basis_type, basis_amount),
  KEY idx_food_nutrient_nutrient (nutrient_code),
  CONSTRAINT fk_fn_food     FOREIGN KEY (food_id)       REFERENCES food (id) ON DELETE CASCADE,
  CONSTRAINT fk_fn_nutrient FOREIGN KEY (nutrient_code) REFERENCES nutrient_info (code),
  CONSTRAINT fk_fn_source   FOREIGN KEY (source_id)     REFERENCES data_source (id)
) ENGINE=InnoDB COMMENT='食物营养成分表';

-- ---------------------------------------------------------------- 视图

-- 含量 + NRV%。能量在数据表中以 kcal 存储而 NRV 以 kJ 规定，用换算系数统一口径
CREATE OR REPLACE VIEW v_food_nutrient_nrv AS
SELECT fn.food_id,
       fn.nutrient_code,
       ni.name        AS nutrient_name,
       ni.unit        AS unit,
       ni.sort_order  AS sort_order,
       fn.amount      AS amount,
       CASE
         WHEN ni.nrv_value IS NULL THEN NULL
         ELSE ROUND(fn.amount * COALESCE(ni.nrv_conversion_factor, 1) / ni.nrv_value * 100, 1)
       END            AS nrv_percent
FROM food_nutrient fn
JOIN nutrient_info ni ON ni.code = fn.nutrient_code
WHERE fn.basis_type = '100G';

-- 营养亮点：只输出达到「富含」条件且配好作用说明的营养素
CREATE OR REPLACE VIEW v_food_highlight AS
SELECT fn.food_id,
       fn.nutrient_code,
       ni.name                   AS nutrient_name,
       ni.unit                   AS unit,
       ni.sort_order             AS sort_order,
       fn.amount                 AS amount,
       ni.rich_rule_type         AS rich_rule_type,
       ni.rich_threshold_percent AS rich_threshold_percent,
       ni.rich_threshold_per_100g AS rich_threshold_per_100g,
       ni.rule_note              AS rule_note,
       CASE
         WHEN ni.nrv_value IS NULL THEN NULL
         ELSE ROUND(fn.amount * COALESCE(ni.nrv_conversion_factor, 1) / ni.nrv_value * 100, 1)
       END                       AS nrv_percent,
       nk.role                   AS role,
       nk.source_name            AS source_name,
       nk.source_url             AS source_url,
       nk.verified_at            AS verified_at
FROM food_nutrient fn
JOIN nutrient_info ni      ON ni.code = fn.nutrient_code
JOIN nutrient_knowledge nk ON nk.nutrient_code = ni.code
WHERE fn.basis_type = '100G'
  AND ( (ni.rich_rule_type = 'NRV_PERCENT'
         AND ni.nrv_value IS NOT NULL
         AND ni.rich_threshold_percent IS NOT NULL
         AND fn.amount * COALESCE(ni.nrv_conversion_factor, 1) / ni.nrv_value * 100
             >= ni.rich_threshold_percent)
     OR (ni.rich_rule_type = 'ABSOLUTE'
         AND ni.rich_threshold_per_100g IS NOT NULL
         AND fn.amount >= ni.rich_threshold_per_100g) );