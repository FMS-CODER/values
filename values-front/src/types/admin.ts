/**
 * 管理端接口类型。
 * 管理端字段比前台多，是因为要支持编辑：前台只展示摘要，
 * 管理端编辑表单需要回填来源、备注、核验状态等原始字段，
 * 因此这些类型与 types/food.ts 分开维护，互不影响。
 */

/** 图片审核状态，与后端 PATCH 接口的取值一致 */
export type ReviewStatus = 'pending' | 'approved' | 'rejected'

/** 分类管理列表项，对应 GET /api/admin/categories 的元素 */
export interface AdminCategory {
  id: number
  code: string
  name: string
  sortOrder: number
  /** 该分类下的食物数量，后端算好；用于展示，也用于提示「为什么删不掉」 */
  foodCount: number
}

/** 分类新增/编辑表单，code 是稳定标识，name 是展示名 */
export interface AdminCategoryForm {
  code: string
  name: string
  sortOrder: number
}

/** 食物管理列表项，对应 GET /api/admin/foods 的 items 元素 */
export interface AdminFoodListItem {
  id: number
  name: string
  nameEn: string | null
  categoryCode: string
  categoryName: string
  imageUrl: string | null
  description: string | null
  state: string | null
  fdcId: number | null
  verified: boolean
  updatedAt: string
}

/** 食物详情，比列表多出编辑所需的全量字段 */
export interface AdminFoodDetail extends AdminFoodListItem {
  categoryId: number
  ndbNumber: number | null
  dataType: string | null
  publicationDate: string | null
  sourceId: number | null
  sourceName: string | null
  sourceRecordId: string | null
  sourceNote: string | null
  claimNote: string | null
}

/**
 * 食物新增/编辑提交体。
 * name 与 categoryId 必填；其余字段可空，后端契约里以 null 表示未填写。
 */
export interface AdminFoodForm {
  name: string
  nameEn: string | null
  categoryId: number
  imageUrl: string | null
  description: string | null
  state: string | null
  fdcId: number | null
  verified: boolean
  sourceNote: string | null
  claimNote: string | null
}

/** 图片审核卡片，对应 GET /api/admin/images 的 items 元素 */
export interface AdminImageItem {
  foodId: number
  foodName: string
  /** 本地相对路径，形如 /foods/74-xxx.webp */
  localPath: string | null
  /** 可直接用于 img src 的地址，可能为 null（表示还没有图） */
  imageUrl: string | null
  sourceName: string | null
  sourceUrl: string | null
  photographer: string | null
  license: string | null
  attribution: string | null
  downloadStatus: string | null
  reviewStatus: ReviewStatus
}

/** 分页响应的公共外壳；hint 只在图片接口出现，用于提示清单缺失 */
export interface Paged<T> {
  items: T[]
  total: number
  page: number
  size: number
  totalPages: number
  hint?: string
}

/** 食物列表查询参数 */
export interface AdminFoodQuery {
  keyword?: string
  categoryCode?: string
  page?: number
  size?: number
}

/** 图片审核列表查询参数；status=all 表示不按审核状态过滤 */
export interface AdminImageQuery {
  status?: ReviewStatus | 'all'
  keyword?: string
  page?: number
  size?: number
}