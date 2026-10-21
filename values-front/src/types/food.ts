/**
 * 后端接口返回值类型。
 * 字段名与后端契约严格一一对应，前端只做展示与筛选，不再自行计算达标结果。
 */

/** 分类选项，对应 GET /api/categories。code 是筛选与配色的稳定标识，name 仅用于展示 */
export interface CategoryOption {
  code: string
  name: string
  sortOrder: number
}

/** 列表卡片中的单项营养素，对应 GET /api/foods 中 nutrients 的元素 */
export interface CardNutrient {
  code: string
  name: string
  unit: string
  amount: number
}

/** 食物列表项，对应 GET /api/foods 的元素 */
export interface FoodSummary {
  id: number
  name: string
  categoryCode: string
  categoryName: string
  imageUrl: string
  description: string
  nutrients: CardNutrient[]
}

/** 详情页营养卡片，对应 GET /api/foods/{id} 中 nutrientTiles 的元素；NRV% 由后端算好 */
export interface NutrientTile {
  code: string
  name: string
  unit: string
  amount: number
  /** 没有规定 NRV 的营养素为 null，页面显示「无 NRV」 */
  nrvPercent: number | null
}

/**
 * 营养亮点，对应 GET /api/foods/{id} 中 highlights 的元素。
 * 后端已按 GB 28050-2025 判定达标，前端只负责展示，不做任何达标计算。
 */
export interface FoodHighlight {
  code: string
  name: string
  unit: string
  amount: number
  nrvPercent: number | null
  ruleLabel: string
  ruleNote: string
  role: string
  sourceName: string
  sourceUrl: string
  verifiedAt: string
}

/** 详情页数据来源信息 */
export interface FoodSource {
  name: string
  /** 官方记录 ID，后端可能返回 null，为空时不展示该行 */
  recordId: string | null
  /** 是否已对照官方来源核验数值 */
  verified: boolean
  note: string
}

/**
 * 「富含」判定所依据的标准。
 * 标准名一定会返回（后端在字典缺失时直接失败），实施日期允许为空。
 */
export interface RuleStandard {
  name: string
  effectiveDate: string | null
}

/** 食物详情，对应 GET /api/foods/{id} 的响应 */
export interface FoodDetail {
  id: number
  name: string
  categoryCode: string
  categoryName: string
  imageUrl: string
  description: string
  /** 食品状态用于明确计量口径，例如「生，带皮」「熟」 */
  state: string
  /** 该食物需要单独说明的营养声称提示，后端可能返回 null，为空时不展示该段 */
  claimNote: string | null
  source: FoodSource
  ruleStandard: RuleStandard
  nutrientTiles: NutrientTile[]
  highlights: FoodHighlight[]
}