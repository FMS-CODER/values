-- 食物营养百科 · 初始化数据（字典与人工整理的中文呈现）
-- 执行方式（PowerShell）：
--   & "D:\mysql\MySQL Server 8.0\bin\mysql.exe" -uroot -p --default-character-set=utf8mb4 -e "source <本文件绝对路径>"
-- 说明：
--   1. 所有 INSERT 都是幂等的（ON DUPLICATE KEY UPDATE），重复执行不会产生重复行；
--   2. 营养数值不在本文件里，由 values-python/importer 从 USDA Foundation Foods 导入到 food_nutrient；
--   3. food 这里只放 9 条人工整理过的食物（中文名、图片、介绍、分类、状态），
--      它们的 fdc_id 指向 USDA 记录，导入脚本会按 fdc_id 补上营养数值并标记为已核验。

USE `values`;

-- ---------------------------------------------------------------- 字典表

INSERT INTO food_category (id, code, name, sort_order) VALUES
(1,'VEGETABLE','蔬菜',1),
(2,'FRUIT','水果',2),
(3,'GRAIN','谷物',3),
(4,'LEGUME','豆类',4),
(5,'NUT_SEED','坚果',5),
(6,'EGG','蛋类',6),
(7,'DAIRY','奶制品',7),
(8,'FISH','鱼类',8),
(9,'MEAT','肉类',9),
(10,'POULTRY','禽类',10),
(11,'OIL_FAT','油脂',11),
(12,'SPICE_HERB','香辛料',12),
(13,'BEVERAGE','饮料',13),
(14,'SOUP_SAUCE','汤酱',14),
(15,'BAKED_SWEET','烘焙糖果',15),
(16,'OTHER','其他',16)
AS new ON DUPLICATE KEY UPDATE code = new.code, name = new.name, sort_order = new.sort_order;

INSERT INTO data_source (id, code, name) VALUES
(1,'USDA_FOUNDATION','USDA FoodData Central')
AS new ON DUPLICATE KEY UPDATE code = new.code, name = new.name;

INSERT INTO rule_source (id, code, name, effective_date, scope_note) VALUES
(1,'GB_28050_2025','GB 28050-2025','2027-03-16','该标准针对预包装食品营养标签，百科页面参考其判定口径')
AS new ON DUPLICATE KEY UPDATE name = new.name, effective_date = new.effective_date, scope_note = new.scope_note;

-- ------------------------------------------------- 营养素基础表（35 项）

-- 只收录会被展示的重点项。USDA 全量 228 项里的细分成分（氨基酸、甾醇、类胡萝卜素、
-- 逐个碳链的脂肪酸等）一概不入库，避免前端出现大量无法解释的孤立数值。
INSERT INTO nutrient_info
 (code, name, name_en, unit, nutrient_group, usda_nutrient_id, usda_number,
  nrv_value, nrv_unit, nrv_conversion_factor, rich_rule_type, rich_threshold_percent,
  rich_threshold_per_100g, rule_source_id, rule_note, show_in_card, sort_order) VALUES
-- 基础成分
('ENERGY','热量','Energy','kcal','PROXIMATE',1008,'208',8400,'kJ',4.184,'NONE',NULL,NULL,1,
 'GB 28050-2025 附录 A：能量 NRV 8400 kJ，不适用「富含」声称',1,1),
('PROTEIN','蛋白质','Protein','g','PROXIMATE',1003,'203',60,'g',NULL,'ABSOLUTE',NULL,12,1,
 'GB 28050-2025：蛋白质每 100g ≥12g',1,2),
('FAT','脂肪','Total lipid (fat)','g','PROXIMATE',1004,'204',60,'g',NULL,'NONE',NULL,NULL,1,
 'GB 28050-2025：脂肪按「低脂」等规则判定，不适用「富含」',1,3),
('CARBOHYDRATE','碳水化合物','Carbohydrate, by difference','g','PROXIMATE',1005,'205',300,'g',NULL,'NONE',NULL,NULL,1,
 'GB 28050-2025 附录 A：碳水化合物没有适用的「富含」规则',1,4),
('FIBER','膳食纤维','Fiber, total dietary','g','PROXIMATE',1079,'291',25,'g',NULL,'ABSOLUTE',NULL,6,1,
 'GB 28050-2025：膳食纤维每 100g ≥6g',0,5),
('SUGAR','总糖','Sugars, Total','g','PROXIMATE',1063,'269.3',NULL,NULL,NULL,'NONE',NULL,NULL,1,
 'GB 28050-2025：糖按「低糖」规则判定，不适用「富含」',0,6),
('WATER','水','Water','g','PROXIMATE',1051,'255',NULL,NULL,NULL,'NONE',NULL,NULL,NULL,
 '没有适用的营养声称规则，仅作含量展示',0,7),
-- 维生素
('VITAMIN_A','维生素 A','Vitamin A, RAE','µg','VITAMIN',1106,'320',800,'µg',NULL,'NRV_PERCENT',30,NULL,1,
 'GB 28050-2025：维生素每 100g ≥30% NRV',0,11),
('VITAMIN_C','维生素 C','Vitamin C, total ascorbic acid','mg','VITAMIN',1162,'401',100,'mg',NULL,'NRV_PERCENT',30,NULL,1,
 'GB 28050-2025：维生素每 100g ≥30% NRV',0,12),
('VITAMIN_D','维生素 D','Vitamin D (D2 + D3)','µg','VITAMIN',1114,'328',10,'µg',NULL,'NRV_PERCENT',30,NULL,1,
 'GB 28050-2025：维生素每 100g ≥30% NRV',0,13),
('VITAMIN_E','维生素 E','Vitamin E (alpha-tocopherol)','mg','VITAMIN',1109,'323',14,'mg',NULL,'NRV_PERCENT',30,NULL,1,
 'GB 28050-2025：维生素每 100g ≥30% NRV',0,14),
('VITAMIN_K','维生素 K','Vitamin K (phylloquinone)','µg','VITAMIN',1185,'430',80,'µg',NULL,'NRV_PERCENT',30,NULL,1,
 'GB 28050-2025：维生素每 100g ≥30% NRV',0,15),
('THIAMIN','维生素 B1','Thiamin','mg','VITAMIN',1165,'404',1.4,'mg',NULL,'NRV_PERCENT',30,NULL,1,
 'GB 28050-2025：维生素每 100g ≥30% NRV',0,16),
('RIBOFLAVIN','维生素 B2','Riboflavin','mg','VITAMIN',1166,'405',1.4,'mg',NULL,'NRV_PERCENT',30,NULL,1,
 'GB 28050-2025：维生素每 100g ≥30% NRV',0,17),
('NIACIN','烟酸','Niacin','mg','VITAMIN',1167,'406',14,'mg',NULL,'NRV_PERCENT',30,NULL,1,
 'GB 28050-2025：维生素每 100g ≥30% NRV',0,18),
('VITAMIN_B6','维生素 B6','Vitamin B-6','mg','VITAMIN',1175,'415',1.4,'mg',NULL,'NRV_PERCENT',30,NULL,1,
 'GB 28050-2025：维生素每 100g ≥30% NRV',0,19),
('FOLATE','叶酸','Folate, total','µg','VITAMIN',1177,'417',400,'µg',NULL,'NRV_PERCENT',30,NULL,1,
 'GB 28050-2025：维生素每 100g ≥30% NRV',0,20),
('VITAMIN_B12','维生素 B12','Vitamin B-12','µg','VITAMIN',1178,'418',2.4,'µg',NULL,'NRV_PERCENT',30,NULL,1,
 'GB 28050-2025：维生素每 100g ≥30% NRV',0,21),
('PANTOTHENIC_ACID','泛酸','Pantothenic acid','mg','VITAMIN',1170,'410',5,'mg',NULL,'NRV_PERCENT',30,NULL,1,
 'GB 28050-2025：维生素每 100g ≥30% NRV',0,22),
-- 矿物质
('SODIUM','钠','Sodium, Na','mg','MINERAL',1093,'307',2000,'mg',NULL,'NONE',NULL,NULL,1,
 'GB 28050-2025：钠按「低钠」规则判定，不作为富含营养素展示',0,31),
('POTASSIUM','钾','Potassium, K','mg','MINERAL',1092,'306',2000,'mg',NULL,'NRV_PERCENT',30,NULL,1,
 'GB 28050-2025：矿物质每 100g ≥30% NRV',0,32),
('CALCIUM','钙','Calcium, Ca','mg','MINERAL',1087,'301',800,'mg',NULL,'NRV_PERCENT',30,NULL,1,
 'GB 28050-2025：矿物质每 100g ≥30% NRV',0,33),
('MAGNESIUM','镁','Magnesium, Mg','mg','MINERAL',1090,'304',300,'mg',NULL,'NRV_PERCENT',30,NULL,1,
 'GB 28050-2025：矿物质每 100g ≥30% NRV',0,34),
('PHOSPHORUS','磷','Phosphorus, P','mg','MINERAL',1091,'305',700,'mg',NULL,'NRV_PERCENT',30,NULL,1,
 'GB 28050-2025：矿物质每 100g ≥30% NRV',0,35),
('IRON','铁','Iron, Fe','mg','MINERAL',1089,'303',15,'mg',NULL,'NRV_PERCENT',30,NULL,1,
 'GB 28050-2025：矿物质每 100g ≥30% NRV',0,36),
('ZINC','锌','Zinc, Zn','mg','MINERAL',1095,'309',15,'mg',NULL,'NRV_PERCENT',30,NULL,1,
 'GB 28050-2025：矿物质每 100g ≥30% NRV',0,37),
('COPPER','铜','Copper, Cu','mg','MINERAL',1098,'312',1.5,'mg',NULL,'NRV_PERCENT',30,NULL,1,
 'GB 28050-2025：矿物质每 100g ≥30% NRV',0,38),
('MANGANESE','锰','Manganese, Mn','mg','MINERAL',1101,'315',3,'mg',NULL,'NRV_PERCENT',30,NULL,1,
 'GB 28050-2025：矿物质每 100g ≥30% NRV',0,39),
('SELENIUM','硒','Selenium, Se','µg','MINERAL',1103,'317',50,'µg',NULL,'NRV_PERCENT',30,NULL,1,
 'GB 28050-2025：矿物质每 100g ≥30% NRV',0,40),
('IODINE','碘','Iodine, I','µg','MINERAL',1100,'314',120,'µg',NULL,'NRV_PERCENT',30,NULL,1,
 'GB 28050-2025：矿物质每 100g ≥30% NRV',0,41),
-- 脂肪酸与胆固醇
('SATURATED_FAT','饱和脂肪','Fatty acids, total saturated','g','FATTY_ACID',1258,'606',20,'g',NULL,'NONE',NULL,NULL,1,
 'GB 28050-2025：饱和脂肪按「低饱和脂肪」规则判定，不适用「富含」',0,51),
('MONOUNSATURATED_FAT','单不饱和脂肪','Fatty acids, total monounsaturated','g','FATTY_ACID',1292,'645',NULL,NULL,NULL,'NONE',NULL,NULL,NULL,
 '没有适用的营养声称规则，仅作含量展示',0,52),
('POLYUNSATURATED_FAT','多不饱和脂肪','Fatty acids, total polyunsaturated','g','FATTY_ACID',1293,'646',NULL,NULL,NULL,'NONE',NULL,NULL,NULL,
 '没有适用的营养声称规则，仅作含量展示',0,53),
('TRANS_FAT','反式脂肪','Fatty acids, total trans','g','FATTY_ACID',1257,'605',NULL,NULL,NULL,'NONE',NULL,NULL,1,
 'GB 28050-2025：反式脂肪按「不含反式脂肪」规则判定，不适用「富含」',0,54),
('CHOLESTEROL','胆固醇','Cholesterol','mg','FATTY_ACID',1253,'601',300,'mg',NULL,'NONE',NULL,NULL,1,
 'GB 28050-2025：胆固醇按「低胆固醇」规则判定，不适用「富含」',0,55)
AS new ON DUPLICATE KEY UPDATE
 name = new.name, name_en = new.name_en, unit = new.unit, nutrient_group = new.nutrient_group,
 usda_nutrient_id = new.usda_nutrient_id, usda_number = new.usda_number,
 nrv_value = new.nrv_value, nrv_unit = new.nrv_unit, nrv_conversion_factor = new.nrv_conversion_factor,
 rich_rule_type = new.rich_rule_type, rich_threshold_percent = new.rich_threshold_percent,
 rich_threshold_per_100g = new.rich_threshold_per_100g, rule_source_id = new.rule_source_id,
 rule_note = new.rule_note, show_in_card = new.show_in_card, sort_order = new.sort_order;

-- ------------------------------------------------- 营养素科普内容与来源

-- 只有配了科普内容的营养素才可能进入「营养亮点」，避免页面出现无法解释的孤立数值。
INSERT INTO nutrient_knowledge (nutrient_code, role, source_name, source_url, verified_at) VALUES
('PROTEIN','是构成和修复人体组织的重要成分，也参与酶、激素等物质的合成。',
 'MedlinePlus','https://medlineplus.gov/ency/article/002467.htm','2026-10-21'),
('FIBER','有助于维持正常排便，并增加饱腹感。',
 'MedlinePlus','https://medlineplus.gov/ency/article/002470.htm','2026-10-21'),
('VITAMIN_A','参与视觉、免疫功能以及细胞的生长和分化。',
 'NIH Office of Dietary Supplements','https://ods.od.nih.gov/factsheets/VitaminA-Consumer/','2026-10-21'),
('VITAMIN_C','参与胶原蛋白合成、免疫功能，也有助于非血红素铁的吸收。',
 'NIH Office of Dietary Supplements','https://ods.od.nih.gov/factsheets/VitaminC-Consumer/','2026-10-21'),
('VITAMIN_D','有助于钙和磷的吸收，维持骨骼与肌肉的正常功能。',
 'NIH Office of Dietary Supplements','https://ods.od.nih.gov/factsheets/VitaminD-Consumer/','2026-10-21'),
('VITAMIN_E','具有抗氧化作用，保护细胞膜中的多不饱和脂肪酸。',
 'NIH Office of Dietary Supplements','https://ods.od.nih.gov/factsheets/VitaminE-Consumer/','2026-10-21'),
('VITAMIN_K','参与凝血因子的合成，也与骨骼健康有关。',
 'NIH Office of Dietary Supplements','https://ods.od.nih.gov/factsheets/VitaminK-Consumer/','2026-10-21'),
('THIAMIN','参与碳水化合物代谢，是神经功能所需能量产生的必需成分。',
 'NIH Office of Dietary Supplements','https://ods.od.nih.gov/factsheets/Thiamin-Consumer/','2026-10-21'),
('RIBOFLAVIN','参与能量代谢，并有助于其他维生素的活化。',
 'NIH Office of Dietary Supplements','https://ods.od.nih.gov/factsheets/Riboflavin-Consumer/','2026-10-21'),
('NIACIN','参与能量代谢与 DNA 修复。',
 'NIH Office of Dietary Supplements','https://ods.od.nih.gov/factsheets/Niacin-Consumer/','2026-10-21'),
('VITAMIN_B6','参与氨基酸和糖原代谢，也支持免疫与神经系统功能。',
 'NIH Office of Dietary Supplements','https://ods.od.nih.gov/factsheets/VitaminB6-Consumer/','2026-10-21'),
('FOLATE','参与核酸和氨基酸代谢，对细胞分裂与红细胞生成很重要。',
 'NIH Office of Dietary Supplements','https://ods.od.nih.gov/factsheets/Folate-Consumer/','2026-10-21'),
('VITAMIN_B12','参与红细胞形成、神经功能以及 DNA 合成。',
 'NIH Office of Dietary Supplements','https://ods.od.nih.gov/factsheets/VitaminB12-Consumer/','2026-10-21'),
('PANTOTHENIC_ACID','参与脂肪酸合成与能量代谢。',
 'NIH Office of Dietary Supplements','https://ods.od.nih.gov/factsheets/PantothenicAcid-Consumer/','2026-10-21'),
('SODIUM','与钾共同维持体液平衡和正常血压所需的渗透压，摄入需要适量。',
 'NIH Office of Dietary Supplements','https://ods.od.nih.gov/factsheets/Sodium-Consumer/','2026-10-21'),
('POTASSIUM','参与正常的神经传导、肌肉收缩以及心脏和肾脏功能。',
 'NIH Office of Dietary Supplements','https://ods.od.nih.gov/factsheets/Potassium-Consumer/','2026-10-21'),
('CALCIUM','是骨骼和牙齿的主要成分，也参与肌肉与神经功能。',
 'NIH Office of Dietary Supplements','https://ods.od.nih.gov/factsheets/Calcium-Consumer/','2026-10-21'),
('MAGNESIUM','参与能量代谢、蛋白质合成，以及肌肉与神经功能。',
 'NIH Office of Dietary Supplements','https://ods.od.nih.gov/factsheets/Magnesium-Consumer/','2026-10-21'),
('PHOSPHORUS','与钙共同构成骨骼和牙齿，并参与能量代谢。',
 'NIH Office of Dietary Supplements','https://ods.od.nih.gov/factsheets/Phosphorus-Consumer/','2026-10-21'),
('IRON','是血红蛋白的组成成分，参与体内氧气的运输。',
 'NIH Office of Dietary Supplements','https://ods.od.nih.gov/factsheets/Iron-Consumer/','2026-10-21'),
('ZINC','参与免疫功能、伤口愈合与细胞分裂。',
 'NIH Office of Dietary Supplements','https://ods.od.nih.gov/factsheets/Zinc-Consumer/','2026-10-21'),
('COPPER','参与铁代谢、抗氧化防御与结缔组织形成。',
 'NIH Office of Dietary Supplements','https://ods.od.nih.gov/factsheets/Copper-Consumer/','2026-10-21'),
('MANGANESE','参与骨骼形成，以及氨基酸与胆固醇的代谢。',
 'NIH Office of Dietary Supplements','https://ods.od.nih.gov/factsheets/Manganese-Consumer/','2026-10-21'),
('SELENIUM','是多种抗氧化酶的组成成分。',
 'NIH Office of Dietary Supplements','https://ods.od.nih.gov/factsheets/Selenium-Consumer/','2026-10-21'),
('IODINE','是甲状腺激素的组成成分，参与生长发育与代谢调节。',
 'NIH Office of Dietary Supplements','https://ods.od.nih.gov/factsheets/Iodine-Consumer/','2026-10-21')
AS new ON DUPLICATE KEY UPDATE
 role = new.role, source_name = new.source_name, source_url = new.source_url, verified_at = new.verified_at;

-- ------------------------------------------------- 人工整理的食物（中文呈现）

-- fdc_id 是对应关系：导入脚本按它把 USDA 的实测营养值挂到这些行上。
-- 豆腐在 Foundation Foods 里没有对应记录，按「对不上就舍弃」的规则不再保留。
INSERT INTO food
 (id, name, name_en, category_id, image_url, description, state, fdc_id, ndb_number, data_type,
  publication_date, source_id, source_record_id, verified, source_note, claim_note) VALUES
(1,'西兰花','Broccoli, raw',1,'/foods/broccoli.jpg','含有维生素 C、膳食纤维和多种矿物质，适合作为日常蔬菜选择。',
 '生，鲜品',747447,NULL,'Foundation','2019-04-01',1,'747447',1,
 'USDA FoodData Central · Foundation Foods，FDC ID 747447。',NULL),
(2,'苹果','Apples, fuji, with skin, raw',2,'/foods/apple.jpg','含有膳食纤维和多种营养成分，适合作为日常水果选择。',
 '生，带皮',1750340,NULL,'Foundation','2019-04-01',1,'1750340',1,
 'USDA FoodData Central · Foundation Foods，FDC ID 1750340（富士苹果，带皮生食）。',
 '苹果含有维生素 C，但含量未达到「富含」的判定条件，因此不列为营养亮点，也不宜称其为「富含维生素 C」。'),
(3,'胡萝卜','Carrots, mature, raw',1,'/foods/carrot.jpg','富含 β-胡萝卜素，口感清甜，适合炒食、蒸煮或加入汤中。',
 '生',2258586,NULL,'Foundation','2020-10-30',1,'2258586',1,
 'USDA FoodData Central · Foundation Foods，FDC ID 2258586（成熟胡萝卜，生）。',NULL),
(4,'鸡胸肉','Chicken, breast, boneless, skinless, raw',10,'/foods/chicken.jpg','高蛋白、低脂肪的禽肉类食材，是日常补充优质蛋白的常见选择。',
 '生，去皮',2646170,NULL,'Foundation','2020-10-30',1,'2646170',1,
 'USDA FoodData Central · Foundation Foods，FDC ID 2646170（去骨去皮鸡胸肉，生）。',NULL),
(5,'糙米','Rice, brown, long grain, unenriched, raw',3,'/foods/brown-rice.jpg','保留麸皮和胚芽的全谷物，膳食纤维含量比精白米更丰富。',
 '生，未烹调',2512380,NULL,'Foundation','2020-10-30',1,'2512380',1,
 'USDA FoodData Central · Foundation Foods，FDC ID 2512380（长粒糙米，生）。',NULL),
(6,'鸡蛋','Egg, whole, raw, frozen, pasteurized',6,'/foods/egg.jpg','优质蛋白与多种脂溶性营养素的来源，日常食用方便。',
 '生，全蛋',323604,NULL,'Foundation','2019-04-01',1,'323604',1,
 'USDA FoodData Central · Foundation Foods，FDC ID 323604（全蛋，生，冷冻巴氏杀菌）。',NULL),
(7,'牛奶','Milk, whole, 3.25% milkfat, with added vitamin D',7,'/foods/milk.jpg','提供蛋白质和钙，是日常奶制品中常见且方便的选择。',
 '全脂',746782,NULL,'Foundation','2019-04-01',1,'746782',1,
 'USDA FoodData Central · Foundation Foods，FDC ID 746782（全脂牛奶，强化维生素 D）。',NULL),
(8,'杏仁','Nuts, almonds, whole, raw',5,'/foods/almond.jpg','富含脂肪和蛋白质的坚果，适合少量食用作为日常加餐。',
 '生，未烘焙',2346393,NULL,'Foundation','2020-10-30',1,'2346393',1,
 'USDA FoodData Central · Foundation Foods，FDC ID 2346393（整粒生杏仁）。',NULL),
(9,'红薯','Sweet potatoes, orange flesh, without skin, raw',1,'/foods/sweet-potato.jpg','含有膳食纤维和碳水化合物，蒸煮后口感绵软、香甜自然。',
 '生，去皮',2346404,NULL,'Foundation','2020-10-30',1,'2346404',1,
 'USDA FoodData Central · Foundation Foods，FDC ID 2346404（橙心红薯，去皮，生）。',NULL)
AS new ON DUPLICATE KEY UPDATE
 name = new.name, name_en = new.name_en, category_id = new.category_id, image_url = new.image_url,
 description = new.description, state = new.state, fdc_id = new.fdc_id, ndb_number = new.ndb_number,
 data_type = new.data_type, publication_date = new.publication_date, source_id = new.source_id,
 source_record_id = new.source_record_id, verified = new.verified,
 source_note = new.source_note, claim_note = new.claim_note;