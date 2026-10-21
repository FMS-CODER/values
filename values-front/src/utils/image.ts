/** 食物图片缺失时统一使用的本地占位图 */
export const FOOD_IMAGE_FALLBACK = '/foods/placeholder.svg'

/**
 * 把可能为空的图片地址解析成可直接用于 src 的字符串。
 * 为空时直接给占位图路径，而不是空字符串——空字符串会让浏览器把当前页面地址当作图片请求，
 * 触发一次失败加载并显示破图标，还会污染控制台。
 */
export function resolveFoodImage(url: string | null): string {
  return url || FOOD_IMAGE_FALLBACK
}

/**
 * 食物图片加载失败时的兜底处理。
 * 通过事件读取触发加载的 img，避免各组件重复编写同一段 DOM 逻辑。
 */
export function handleFoodImageError(event: Event): void {
  const image = event.currentTarget
  if (!(image instanceof HTMLImageElement)) return

  // 占位图自身也可能加载失败，这里避免重复赋值造成循环触发
  if (!image.src.endsWith(FOOD_IMAGE_FALLBACK)) {
    image.src = FOOD_IMAGE_FALLBACK
  }
}
