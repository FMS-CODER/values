/**
 * 营养素 code → 营养卡片配色类名。
 * 配色沿用 main.css 中既有的 .nutrient-tile.is-* 定义，新增营养素时只需在这里补一行映射。
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