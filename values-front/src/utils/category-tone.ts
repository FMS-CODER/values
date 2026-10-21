/**
 * 分类 code → 分类标签配色类名。
 * 配色沿用 main.css 中既有的 .category-tag.is-* 定义，这里只做 code 到类名的映射。
 * 分类由 9 类扩到 16 类，这里补齐全部 code，避免任何分类掉进无样式的默认外观。
 */
const CATEGORY_TONES: Record<string, string> = {
  VEGETABLE: 'is-vegetable',
  FRUIT: 'is-fruit',
  GRAIN: 'is-grain',
  LEGUME: 'is-legume',
  NUT_SEED: 'is-nut-seed',
  EGG: 'is-egg',
  DAIRY: 'is-dairy',
  FISH: 'is-fish',
  MEAT: 'is-meat',
  POULTRY: 'is-poultry',
  OIL_FAT: 'is-oil-fat',
  SPICE_HERB: 'is-spice-herb',
  BEVERAGE: 'is-beverage',
  SOUP_SAUCE: 'is-soup-sauce',
  BAKED_SWEET: 'is-baked-sweet',
  OTHER: 'is-other',
}

/** 未知 code 回退到「其他」配色，避免后端新增分类时标签失去样式 */
export function categoryTone(code: string): string {
  return CATEGORY_TONES[code] ?? CATEGORY_TONES.OTHER
}