/**
 * 营养素 code → 营养卡片配色类名。
 * 配色沿用 main.css 中既有的 .nutrition-item.is-* 定义。
 * 仅用于列表卡片固定的 4 项；详情页营养格改为按组配色，见 nutrientGroupTone。
 */
const NUTRIENT_TONES: Record<string, string> = {
  ENERGY: 'is-calories',
  PROTEIN: 'is-protein',
  FAT: 'is-fat',
  CARBOHYDRATE: 'is-carbohydrates',
  FIBER: 'is-fiber',
  VITAMIN_C: 'is-vitamin-c',
  POTASSIUM: 'is-potassium',
}

/** 未知 code 返回空类名，卡片用默认底色渲染，不影响布局 */
export function nutrientTone(code: string): string {
  return NUTRIENT_TONES[code] ?? ''
}

/**
 * 详情页营养素分组：中文标题与展示顺序。
 * 后端只返回英文 group code，不返回中文名，因此中文映射由前端负责。
 * 顺序固定为 基础成分 → 维生素 → 矿物质 → 脂肪酸与胆固醇。
 */
export const NUTRIENT_GROUPS: { code: string; title: string }[] = [
  { code: 'PROXIMATE', title: '基础成分' },
  { code: 'VITAMIN', title: '维生素' },
  { code: 'MINERAL', title: '矿物质' },
  { code: 'FATTY_ACID', title: '脂肪酸与胆固醇' },
]

/**
 * 分组 → 营养格配色类名。
 * 详情页有 35 种营养素，一色一码无法维护也无区分意义，改为 4 组 4 色，
 * 让配色传递「属于哪一类」而非「具体是哪种」，沿用既有浅色系。
 */
const NUTRIENT_GROUP_TONES: Record<string, string> = {
  PROXIMATE: 'is-proximate',
  VITAMIN: 'is-vitamin',
  MINERAL: 'is-mineral',
  FATTY_ACID: 'is-fatty-acid',
}

/** 未知分组回退到基础成分配色，保证营养格始终有底色 */
export function nutrientGroupTone(group: string): string {
  return NUTRIENT_GROUP_TONES[group] ?? NUTRIENT_GROUP_TONES.PROXIMATE
}