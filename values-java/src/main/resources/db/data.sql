-- 食物营养百科 · 初始化数据
-- 执行方式（PowerShell）：
--   & "D:\mysql\MySQL Server 8.0\bin\mysql.exe" -uroot -p --default-character-set=utf8mb4 -e "source <本文件绝对路径>"
-- 说明：所有 INSERT 都是幂等的（ON DUPLICATE KEY UPDATE），重复执行不会产生重复行。

USE `values`;

-- ---------------------------------------------------------------- 字典表

INSERT INTO food_category (id, code, name, sort_order) VALUES
(1,'VEGETABLE','蔬菜',1),
(2,'FRUIT','水果',2),
(3,'GRAIN','谷物',3),
(4,'MEAT','肉类',4),
(5,'EGG','蛋类',5),
(6,'SOY','豆制品',6),
(7,'DAIRY','奶制品',7),
(8,'NUT','坚果',8),
(9,'OTHER','其他',9)
AS new ON DUPLICATE KEY UPDATE code = new.code, name = new.name, sort_order = new.sort_order;

INSERT INTO data_source (id, code, name) VALUES
(1,'DEMO','界面演示数据'),
(2,'USDA_SR_LEGACY','USDA SR Legacy')
AS new ON DUPLICATE KEY UPDATE code = new.code, name = new.name;

INSERT INTO rule_source (id, code, name, effective_date, scope_note) VALUES
(1,'GB_28050_2025','GB 28050-2025','2027-03-16','该标准针对预包装食品营养标签，百科页面参考其判定口径')
AS new ON DUPLICATE KEY UPDATE name = new.name, effective_date = new.effective_date, scope_note = new.scope_note;

-- ---------------------------------------------------------- 营养素与规则

INSERT INTO nutrient_info
 (code, name, unit, nutrient_group, nrv_value, nrv_unit, nrv_conversion_factor,
  rich_rule_type, rich_threshold_percent, rich_threshold_per_100g, rule_source_id, rule_note,
  show_in_card, sort_order) VALUES
('ENERGY','热量','kcal','OTHER',8400,'kJ',4.184,'NONE',NULL,NULL,1,
 'GB 28050-2025 附录 A：能量 NRV 8400 kJ，不适用「富含」声称',1,1),
('PROTEIN','蛋白质','g','PROTEIN',60,'g',NULL,'ABSOLUTE',NULL,12,1,
 'GB 28050-2025：蛋白质每 100g ≥12g',1,2),
('FAT','脂肪','g','OTHER',60,'g',NULL,'NONE',NULL,NULL,1,
 'GB 28050-2025：脂肪按「低脂」等规则判定，不适用「富含」',1,3),
('CARBOHYDRATE','碳水化合物','g','OTHER',300,'g',NULL,'NONE',NULL,NULL,1,
 'GB 28050-2025 附录 A：碳水化合物没有适用的「富含」规则',1,4),
('FIBER','膳食纤维','g','FIBER',25,'g',NULL,'ABSOLUTE',NULL,6,1,
 'GB 28050-2025：膳食纤维每 100g ≥6g',0,5),
('VITAMIN_C','维生素 C','mg','VITAMIN',100,'mg',NULL,'NRV_PERCENT',30,NULL,1,
 'GB 28050-2025：维生素每 100g ≥30% NRV',0,6),
('POTASSIUM','钾','mg','MINERAL',2000,'mg',NULL,'NRV_PERCENT',30,NULL,1,
 'GB 28050-2025：矿物质每 100g ≥30% NRV',0,7)
AS new ON DUPLICATE KEY UPDATE
 name = new.name, unit = new.unit, nutrient_group = new.nutrient_group,
 nrv_value = new.nrv_value, nrv_unit = new.nrv_unit, nrv_conversion_factor = new.nrv_conversion_factor,
 rich_rule_type = new.rich_rule_type, rich_threshold_percent = new.rich_threshold_percent,
 rich_threshold_per_100g = new.rich_threshold_per_100g, rule_source_id = new.rule_source_id,
 rule_note = new.rule_note, show_in_card = new.show_in_card, sort_order = new.sort_order;

INSERT INTO nutrient_knowledge (nutrient_code, role, source_name, source_url, verified_at) VALUES
('PROTEIN','是构成和修复人体组织的重要成分，也参与酶、激素等物质的合成。',
 'MedlinePlus','https://medlineplus.gov/ency/article/002467.htm','2026-10-21'),
('FIBER','有助于维持正常排便，并增加饱腹感。',
 'MedlinePlus','https://medlineplus.gov/ency/article/002470.htm','2026-10-21'),
('VITAMIN_C','参与胶原蛋白合成、免疫功能，也有助于非血红素铁的吸收。',
 'NIH Office of Dietary Supplements','https://ods.od.nih.gov/factsheets/VitaminC-Consumer/','2026-10-21'),
('POTASSIUM','参与正常的神经传导、肌肉收缩以及心脏和肾脏功能。',
 'NIH Office of Dietary Supplements','https://ods.od.nih.gov/factsheets/Potassium-Consumer/','2026-10-21')
AS new ON DUPLICATE KEY UPDATE
 role = new.role, source_name = new.source_name, source_url = new.source_url, verified_at = new.verified_at;

-- ---------------------------------------------------------- 食物与含量

INSERT INTO food
 (id, name, category_id, image_url, description, state, source_id, source_record_id,
  verified, source_note, claim_note) VALUES
(1,'西兰花',1,'/foods/broccoli.jpg','含有维生素 C、膳食纤维和多种矿物质，适合作为日常蔬菜选择。',
 '生，鲜品',1,NULL,0,'界面演示数据，待按食品状态与可靠营养数据库校验。',NULL),
(2,'苹果',2,'/foods/apple.jpg','含有膳食纤维和多种营养成分，适合作为日常水果选择。',
 '生，带皮',2,'171688',1,'USDA SR Legacy 食品记录，FDC ID 171688。数值为示例引用，正式使用前请再次核对。',
 '苹果含有维生素 C，但含量未达到「富含」的判定条件，因此不列为营养亮点，也不宜称其为「富含维生素 C」。'),
(3,'胡萝卜',1,'/foods/carrot.jpg','富含 β-胡萝卜素，口感清甜，适合炒食、蒸煮或加入汤中。',
 '生，去皮',1,NULL,0,'界面演示数据，待按食品状态与可靠营养数据库校验。',NULL),
(4,'鸡胸肉',4,'/foods/chicken.jpg','高蛋白、低脂肪的禽肉类食材，是日常补充优质蛋白的常见选择。',
 '生，去皮',1,NULL,0,'界面演示数据，待按食品状态与可靠营养数据库校验。',NULL),
(5,'糙米',3,'/foods/brown-rice.jpg','保留麸皮和胚芽的全谷物，膳食纤维含量比精白米更丰富。',
 '熟',1,NULL,0,'界面演示数据，待按食品状态与可靠营养数据库校验。',NULL),
(6,'鸡蛋',5,'/foods/egg.jpg','优质蛋白与多种脂溶性营养素的来源，日常食用方便。',
 '生，全蛋',1,NULL,0,'界面演示数据，待按食品状态与可靠营养数据库校验。',NULL),
(7,'豆腐',6,'/foods/tofu.jpg','以大豆为原料的豆制品，提供植物蛋白和钙等营养成分。',
 '北豆腐',1,NULL,0,'界面演示数据，待按食品状态与可靠营养数据库校验。',NULL),
(8,'牛奶',7,'/foods/milk.jpg','提供蛋白质和钙，是日常奶制品中常见且方便的选择。',
 '全脂',1,NULL,0,'界面演示数据，待按食品状态与可靠营养数据库校验。',NULL),
(9,'杏仁',8,'/foods/almond.jpg','富含脂肪和蛋白质的坚果，适合少量食用作为日常加餐。',
 '生，未烘焙',1,NULL,0,'界面演示数据，待按食品状态与可靠营养数据库校验。',NULL),
(10,'红薯',1,'/foods/sweet-potato.jpg','含有膳食纤维和碳水化合物，蒸煮后口感绵软、香甜自然。',
 '生，带皮',1,NULL,0,'界面演示数据，待按食品状态与可靠营养数据库校验。',NULL)
AS new ON DUPLICATE KEY UPDATE
 name = new.name, category_id = new.category_id, image_url = new.image_url,
 description = new.description, state = new.state, source_id = new.source_id,
 source_record_id = new.source_record_id, verified = new.verified,
 source_note = new.source_note, claim_note = new.claim_note;

INSERT INTO food_nutrient (food_id, nutrient_code, amount) VALUES
(1,'ENERGY',34),(1,'PROTEIN',2.8),(1,'FAT',0.4),(1,'CARBOHYDRATE',6.6),(1,'FIBER',2.6),(1,'VITAMIN_C',89.2),(1,'POTASSIUM',316),
(2,'ENERGY',52),(2,'PROTEIN',0.3),(2,'FAT',0.2),(2,'CARBOHYDRATE',13.8),(2,'FIBER',2.4),(2,'VITAMIN_C',4.6),(2,'POTASSIUM',107),
(3,'ENERGY',41),(3,'PROTEIN',0.9),(3,'FAT',0.2),(3,'CARBOHYDRATE',9.6),(3,'FIBER',2.8),(3,'VITAMIN_C',5.9),(3,'POTASSIUM',320),
(4,'ENERGY',133),(4,'PROTEIN',24.6),(4,'FAT',2.6),(4,'CARBOHYDRATE',0),(4,'FIBER',0),(4,'VITAMIN_C',0),(4,'POTASSIUM',256),
(5,'ENERGY',111),(5,'PROTEIN',2.6),(5,'FAT',0.9),(5,'CARBOHYDRATE',23.5),(5,'FIBER',1.8),(5,'VITAMIN_C',0),(5,'POTASSIUM',43),
(6,'ENERGY',144),(6,'PROTEIN',12.6),(6,'FAT',9.5),(6,'CARBOHYDRATE',1.1),(6,'FIBER',0),(6,'VITAMIN_C',0),(6,'POTASSIUM',126),
(7,'ENERGY',76),(7,'PROTEIN',8.1),(7,'FAT',4.2),(7,'CARBOHYDRATE',1.9),(7,'FIBER',0.3),(7,'VITAMIN_C',0.2),(7,'POTASSIUM',121),
(8,'ENERGY',54),(8,'PROTEIN',3),(8,'FAT',3.2),(8,'CARBOHYDRATE',4.8),(8,'FIBER',0),(8,'VITAMIN_C',0),(8,'POTASSIUM',150),
(9,'ENERGY',579),(9,'PROTEIN',21.2),(9,'FAT',49.9),(9,'CARBOHYDRATE',21.6),(9,'FIBER',12.5),(9,'VITAMIN_C',0),(9,'POTASSIUM',733),
(10,'ENERGY',86),(10,'PROTEIN',1.6),(10,'FAT',0.1),(10,'CARBOHYDRATE',20.1),(10,'FIBER',3),(10,'VITAMIN_C',2.4),(10,'POTASSIUM',337)
AS new ON DUPLICATE KEY UPDATE amount = new.amount;