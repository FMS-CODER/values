/** 食物图片缺失时统一使用的本地占位图 */
const FOOD_IMAGE_FALLBACK = '/foods/placeholder.svg'

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
