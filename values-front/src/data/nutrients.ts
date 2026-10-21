/** 所有营养数值统一按「每 100g 可食部分」展示 */
export const NUTRIENT_BASIS = '每 100g 可食部分'

export const NUTRIENT_CODES = [
  'calories',
  'protein',
  'fat',
  'carbohydrates',
  'fiber',
  'vitaminC',
  'potassium',
] as const

export type NutrientCode = (typeof NUTRIENT_CODES)[number]

/**
 * 「富含 / 高」的判定口径。
 * NRV_PERCENT：每 100g 达到一定比例的营养素参考值；
 * ABSOLUTE：每 100g 达到规定的绝对含量；
 * NONE：该成分没有可套用的判定规则，不应用自定义百分比判断「富含」。
 */
export type RichRuleType = 'NRV_PERCENT' | 'ABSOLUTE' | 'NONE'

/**
 * 营养素基础表，对应 nutrient_info。
 * 除名称、单位与配色外，这里保存「富含」判定所需的规则字段，
 * 新增营养素时只改数据，不需要修改页面或后续的服务端代码。
 */
export interface NutrientInfo {
  name: string
  unit: string
  /** 对应 main.css 中的浅色营养卡片样式 */
  tone: string
  /** 营养素参考值；没有规定 NRV 的成分留空 */
  nrvValue?: number
  richRuleType: RichRuleType
  /** NRV_PERCENT 口径的阈值，30 表示每 100g ≥30% NRV */
  richThresholdPercent?: number
  /** ABSOLUTE 口径的阈值，单位与 unit 一致 */
  richThresholdPer100g?: number
  /** 判定依据的出处，便于回溯与更新 */
  ruleSource: string
}

/** 判定规则的出处，供页面展示与追溯 */
export const RICH_RULE_SOURCE = {
  label: 'GB 28050-2025',
  url: 'https://www.nhc.gov.cn/sps/c100087/202509/470fa4ff5de14dd38619223cce9da4e7.shtml',
}

/** NRV% 计算时统一使用的小数位处理：保留 1 位小数 */
function roundPercent(value: number): number {
  return Math.round(value * 10) / 10
}

/**
 * 营养素基础表。
 * NRV 取自 GB 28050-2025 附录 A；维生素与矿物质按 ≥30% NRV 判定「富含」，
 * 蛋白质与膳食纤维按标准中的绝对含量要求判定，
 * 热量、脂肪、碳水化合物暂无可套用的「富含」规则，因此标记为 NONE。
 */
export const NUTRIENT_INFO: Record<NutrientCode, NutrientInfo> = {
  calories: {
    name: '热量',
    unit: 'kcal',
    tone: 'is-calories',
    nrvValue: 8400,
    richRuleType: 'NONE',
    ruleSource: 'GB 28050-2025 附录 A（能量 NRV 8400 kJ，不适用「富含」声称）',
  },
  protein: {
    name: '蛋白质',
    unit: 'g',
    tone: 'is-protein',
    nrvValue: 60,
    richRuleType: 'ABSOLUTE',
    richThresholdPer100g: 12,
    ruleSource: 'GB 28050-2025 蛋白质「富含」判定：≥12g/100g',
  },
  fat: {
    name: '脂肪',
    unit: 'g',
    tone: 'is-fat',
    nrvValue: 60,
    richRuleType: 'NONE',
    ruleSource: 'GB 28050-2025 附录 A（脂肪按「低脂」等规则判定，不适用「富含」）',
  },
  carbohydrates: {
    name: '碳水化合物',
    unit: 'g',
    tone: 'is-carbohydrates',
    nrvValue: 300,
    richRuleType: 'NONE',
    ruleSource: 'GB 28050-2025 附录 A（碳水化合物无适用的「富含」规则）',
  },
  fiber: {
    name: '膳食纤维',
    unit: 'g',
    tone: 'is-fiber',
    nrvValue: 25,
    richRuleType: 'ABSOLUTE',
    richThresholdPer100g: 6,
    ruleSource: 'GB 28050-2025 膳食纤维「富含」判定：≥6g/100g',
  },
  vitaminC: {
    name: '维生素 C',
    unit: 'mg',
    tone: 'is-vitamin-c',
    nrvValue: 100,
    richRuleType: 'NRV_PERCENT',
    richThresholdPercent: 30,
    ruleSource: 'GB 28050-2025 维生素「富含」判定：≥30% NRV/100g',
  },
  potassium: {
    name: '钾',
    unit: 'mg',
    tone: 'is-potassium',
    nrvValue: 2000,
    richRuleType: 'NRV_PERCENT',
    richThresholdPercent: 30,
    ruleSource: 'GB 28050-2025 矿物质「富含」判定：≥30% NRV/100g',
  },
}

/** 营养素知识条目：在基础信息上补充生理作用与可追溯来源 */
export interface NutrientKnowledge extends NutrientInfo {
  role: string
  sourceName: string
  sourceUrl: string
  verifiedAt: string
}

/** 只有配好作用说明与来源的营养素才会出现在「营养亮点」中 */
export const KNOWLEDGE_CODES = ['protein', 'fiber', 'vitaminC', 'potassium'] as const

export type KnowledgeCode = (typeof KNOWLEDGE_CODES)[number]

/**
 * 营养素知识表。
 * 名称、单位和配色复用 NUTRIENT_INFO，避免同一营养素维护两份基础信息；
 * 核验日期表示最近一次整理来源内容的时间。
 */
export const NUTRIENT_KNOWLEDGE: Record<KnowledgeCode, NutrientKnowledge> = {
  protein: {
    ...NUTRIENT_INFO.protein,
    role: '是构成和修复人体组织的重要成分，也参与酶、激素等物质的合成。',
    sourceName: 'MedlinePlus',
    sourceUrl: 'https://medlineplus.gov/ency/article/002467.htm',
    verifiedAt: '2026-10-21',
  },
  fiber: {
    ...NUTRIENT_INFO.fiber,
    role: '有助于维持正常排便，并增加饱腹感。',
    sourceName: 'MedlinePlus',
    sourceUrl: 'https://medlineplus.gov/ency/article/002470.htm',
    verifiedAt: '2026-10-21',
  },
  vitaminC: {
    ...NUTRIENT_INFO.vitaminC,
    role: '参与胶原蛋白合成、免疫功能，也有助于非血红素铁的吸收。',
    sourceName: 'NIH Office of Dietary Supplements',
    sourceUrl: 'https://ods.od.nih.gov/factsheets/VitaminC-Consumer/',
    verifiedAt: '2026-10-21',
  },
  potassium: {
    ...NUTRIENT_INFO.potassium,
    role: '参与正常的神经传导、肌肉收缩以及心脏和肾脏功能。',
    sourceName: 'NIH Office of Dietary Supplements',
    sourceUrl: 'https://ods.od.nih.gov/factsheets/Potassium-Consumer/',
    verifiedAt: '2026-10-21',
  },
}

/**
 * 食物营养成分表。
 * 结构对应 food_nutrient：食物 ID → 营养素编码 → 每 100g 含量。
 * 除苹果参考 USDA SR Legacy 记录外，其余为界面演示数据。
 */
export const FOOD_NUTRIENTS: Record<number, Record<NutrientCode, number>> = {
  1: {
    calories: 34,
    protein: 2.8,
    fat: 0.4,
    carbohydrates: 6.6,
    fiber: 2.6,
    vitaminC: 89.2,
    potassium: 316,
  },
  2: {
    calories: 52,
    protein: 0.3,
    fat: 0.2,
    carbohydrates: 13.8,
    fiber: 2.4,
    vitaminC: 4.6,
    potassium: 107,
  },
  3: {
    calories: 41,
    protein: 0.9,
    fat: 0.2,
    carbohydrates: 9.6,
    fiber: 2.8,
    vitaminC: 5.9,
    potassium: 320,
  },
  4: {
    calories: 133,
    protein: 24.6,
    fat: 2.6,
    carbohydrates: 0,
    fiber: 0,
    vitaminC: 0,
    potassium: 256,
  },
  5: {
    calories: 111,
    protein: 2.6,
    fat: 0.9,
    carbohydrates: 23.5,
    fiber: 1.8,
    vitaminC: 0,
    potassium: 43,
  },
  6: {
    calories: 144,
    protein: 12.6,
    fat: 9.5,
    carbohydrates: 1.1,
    fiber: 0,
    vitaminC: 0,
    potassium: 126,
  },
  7: {
    calories: 76,
    protein: 8.1,
    fat: 4.2,
    carbohydrates: 1.9,
    fiber: 0.3,
    vitaminC: 0.2,
    potassium: 121,
  },
  8: {
    calories: 54,
    protein: 3,
    fat: 3.2,
    carbohydrates: 4.8,
    fiber: 0,
    vitaminC: 0,
    potassium: 150,
  },
  9: {
    calories: 579,
    protein: 21.2,
    fat: 49.9,
    carbohydrates: 21.6,
    fiber: 12.5,
    vitaminC: 0,
    potassium: 733,
  },
  10: {
    calories: 86,
    protein: 1.6,
    fat: 0.1,
    carbohydrates: 20.1,
    fiber: 3,
    vitaminC: 2.4,
    potassium: 337,
  },
}

/**
 * 读取指定食物在每 100g 基准下的营养素含量。
 * 未收录的营养素返回 0；单位统一从 NUTRIENT_INFO 读取，避免数据表重复保存单位。
 */
export function getNutrientAmount(foodId: number, code: NutrientCode): number {
  return FOOD_NUTRIENTS[foodId]?.[code] ?? 0
}

/**
 * 计算 NRV%：含量 ÷ NRV × 100%。
 * 数据表以 kcal 记录能量而 NRV 以 kJ 规定，因此能量需要先按 1 kcal = 4.184 kJ 换算；
 * 没有规定 NRV 的营养素返回 null，页面不展示百分比，也不据此判断「富含」。
 */
export function getNrvPercent(foodId: number, code: NutrientCode): number | null {
  const { nrvValue } = NUTRIENT_INFO[code]
  if (!nrvValue) return null

  const amount = getNutrientAmount(foodId, code)
  const comparable = code === 'calories' ? amount * 4.184 : amount
  return roundPercent((comparable / nrvValue) * 100)
}

/** 判定口径的可读说明，用于在页面上说明某个营养素为什么算「富含」 */
export function getRichRuleLabel(code: NutrientCode): string {
  const info = NUTRIENT_INFO[code]

  if (info.richRuleType === 'NRV_PERCENT') {
    return `每 100g ≥${info.richThresholdPercent}% NRV`
  }
  if (info.richRuleType === 'ABSOLUTE') {
    return `每 100g ≥${info.richThresholdPer100g}${info.unit}`
  }
  return '暂无适用判定规则'
}

/**
 * 判断某个食物中的某营养素是否达到「富含」条件。
 * 没有判定规则的成分一律返回 false，避免用自定百分比得出「富含」结论。
 */
export function isRichNutrient(foodId: number, code: NutrientCode): boolean {
  const info = NUTRIENT_INFO[code]

  if (info.richRuleType === 'NRV_PERCENT') {
    const percent = getNrvPercent(foodId, code)
    return percent !== null && percent >= (info.richThresholdPercent ?? Number.POSITIVE_INFINITY)
  }

  if (info.richRuleType === 'ABSOLUTE') {
    const amount = getNutrientAmount(foodId, code)
    return amount >= (info.richThresholdPer100g ?? Number.POSITIVE_INFINITY)
  }

  return false
}

/** 营养亮点条目：达标结果 + 含量 + 判定依据 + 经核验的营养作用 */
export interface NutrientHighlight extends NutrientKnowledge {
  code: KnowledgeCode
  amount: number
  nrvPercent: number | null
  ruleLabel: string
}

/**
 * 汇总某个食物的营养亮点。
 * 只遍历有作用说明的营养素，页面因此不会出现无法解释的孤立数值；
 * 未达标的数据不出现在结果中，但仍完整保存在 FOOD_NUTRIENTS 里供后续扩展。
 */
export function getFoodHighlights(foodId: number): NutrientHighlight[] {
  return KNOWLEDGE_CODES.flatMap((code) => {
    if (!isRichNutrient(foodId, code)) return []

    return [
      {
        ...NUTRIENT_KNOWLEDGE[code],
        code,
        amount: getNutrientAmount(foodId, code),
        nrvPercent: getNrvPercent(foodId, code),
        ruleLabel: getRichRuleLabel(code),
      },
    ]
  })
}