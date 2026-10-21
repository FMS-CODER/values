import { request, requestJson } from '@/services/http'
import type {
  AdminCategory,
  AdminCategoryForm,
  AdminFoodDetail,
  AdminFoodForm,
  AdminFoodListItem,
  AdminFoodQuery,
  AdminImageItem,
  AdminImageQuery,
  Paged,
  ReviewStatus,
} from '@/types/admin'

/**
 * 拼查询串：跳过空值，避免出现 keyword=undefined 或空参数污染后端解析。
 * 页码与条数按数字处理，其余保持原样。
 */
function buildQuery(params: Record<string, string | number | undefined | null>): string {
  const search = new URLSearchParams()

  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null) continue
    const text = String(value).trim()
    if (!text) continue
    search.set(key, text)
  }

  const query = search.toString()
  return query ? `?${query}` : ''
}

/* ---------- 分类 ---------- */

export function fetchAdminCategories(): Promise<AdminCategory[]> {
  return request<AdminCategory[]>('/api/admin/categories')
}

export function createCategory(form: AdminCategoryForm): Promise<AdminCategory> {
  return requestJson<AdminCategory>('/api/admin/categories', 'POST', form)
}

export function updateCategory(id: number, form: AdminCategoryForm): Promise<AdminCategory> {
  return requestJson<AdminCategory>(`/api/admin/categories/${id}`, 'PUT', form)
}

/** 删除成功返回 204，调用方不需要处理返回值 */
export function deleteCategory(id: number): Promise<void> {
  return requestJson<void>(`/api/admin/categories/${id}`, 'DELETE')
}

/* ---------- 食物 ---------- */

export function fetchAdminFoods(query: AdminFoodQuery): Promise<Paged<AdminFoodListItem>> {
  return request<Paged<AdminFoodListItem>>(`/api/admin/foods${buildQuery({ ...query })}`)
}

export function fetchAdminFood(id: number): Promise<AdminFoodDetail> {
  return request<AdminFoodDetail>(`/api/admin/foods/${id}`)
}

export function createFood(form: AdminFoodForm): Promise<AdminFoodDetail> {
  return requestJson<AdminFoodDetail>('/api/admin/foods', 'POST', form)
}

export function updateFood(id: number, form: AdminFoodForm): Promise<AdminFoodDetail> {
  return requestJson<AdminFoodDetail>(`/api/admin/foods/${id}`, 'PUT', form)
}

export function deleteFood(id: number): Promise<void> {
  return requestJson<void>(`/api/admin/foods/${id}`, 'DELETE')
}

/* ---------- 图片审核 ---------- */

export function fetchAdminImages(query: AdminImageQuery): Promise<Paged<AdminImageItem>> {
  return request<Paged<AdminImageItem>>(`/api/admin/images${buildQuery({ ...query })}`)
}

export function reviewImage(
  foodId: number,
  status: Extract<ReviewStatus, 'approved' | 'rejected'>,
): Promise<AdminImageItem> {
  return requestJson<AdminImageItem>(`/api/admin/images/${foodId}/review`, 'PATCH', { status })
}