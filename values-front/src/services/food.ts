import { request } from '@/services/http'
import type { CategoryOption, FoodDetail, FoodSummary } from '@/types/food'

/** 拉取全部分类，用于筛选标签 */
export function fetchCategories(): Promise<CategoryOption[]> {
  return request<CategoryOption[]>('/api/categories')
}

/** 拉取食物列表，供列表页与首页共用 */
export function fetchFoods(): Promise<FoodSummary[]> {
  return request<FoodSummary[]>('/api/foods')
}

/** 按 ID 拉取食物详情；ID 不存在时后端返回 404，由调用方处理 */
export function fetchFoodDetail(id: number): Promise<FoodDetail> {
  return request<FoodDetail>(`/api/foods/${id}`)
}