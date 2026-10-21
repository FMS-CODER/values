/**
 * 分类 code → 分类标签配色类名。
 * 配色沿用 main.css 中既有的 .category-tag.is-* 定义，这里只做 code 到类名的映射。
 */
const CATEGORY_TONES: Record<string, string> = {
  VEGETABLE: 'is-vegetable',
  FRUIT: 'is-fruit',
  GRAIN: 'is-grain',
  MEAT: 'is-meat',
  EGG: 'is-egg',
  SOY: 'is-soy',
  DAIRY: 'is-dairy',
  NUT: 'is-nut',
  OTHER: 'is-other',
}

/** 未知 code 回退到「其他」配色，避免后端新增分类时标签失去样式 */
export function categoryTone(code: string): string {
  return CATEGORY_TONES[code] ?? CATEGORY_TONES.OTHER
}