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
  /**
   * 含量可能为 null：接口固定返回 4 个槽位，但 USDA 源数据本身缺少该项，
   * 后端不对缺失值做填充，前端需按「无数据」处理而不是当作 0。
   */
  amount: number | null
}

/** 食物列表项，对应 GET /api/foods 的元素 */
export interface FoodSummary {
  id: number
  name: string
  categoryCode: string
  categoryName: string
  /** 仅人工整理的少量食物有配图，USDA 批量数据无图片，故可能为 null */
  imageUrl: string | null
  /** USDA 批量数据没有中文介绍，故可能为 null；为空时列表卡片不渲染该行 */
  description: string | null
  nutrients: CardNutrient[]
}

/** 详情页营养卡片，对应 GET /api/foods/{id} 中 nutrientTiles 的元素；NRV% 由后端算好 */
export interface NutrientTile {
  code: string
  name: string
  unit: string
  amount: number
  /**
   * 营养素所属分组，取值 PROXIMATE / VITAMIN / MINERAL / FATTY_ACID。
   * 后端只返回英文 code，中文标题由前端映射；详情页据此分组展示并按组配色。
   */
  group: string
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
  /** 同列表项：USDA 批量数据无配图，为空时详情页展示本地占位图 */
  imageUrl: string | null
  /** 同列表项：为空时详情页不渲染介绍段落 */
  description: string | null
  /**
   * 食品状态用于明确计量口径，例如「生，带皮」「熟」。
   * 部分来源数据未标注状态，此时为 null，详情页不渲染状态徽标。
   */
  state: string | null
  /** 该食物需要单独说明的营养声称提示，后端可能返回 null，为空时不展示该段 */
  claimNote: string | null
  source: FoodSource
  ruleStandard: RuleStandard
  nutrientTiles: NutrientTile[]
  highlights: FoodHighlight[]
}