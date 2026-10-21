import { defineStore } from 'pinia'
import { fetchCategories, fetchFoods } from '@/services/food'
import type { CategoryOption, FoodSummary } from '@/types/food'

/**
 * 分类筛选的「全部」伪选项 code。
 * 它只用于前端筛选，不来自后端，单独定义避免各处写魔法字符串。
 */
export const ALL_CATEGORY_CODE = 'ALL'

interface FoodState {
  foods: FoodSummary[]
  categories: CategoryOption[]
  loading: boolean
  /** 加载失败时面向用户的可读提示，空字符串表示无错误 */
  error: string
  searchKeyword: string
  /** 当前选中的分类 code，默认为「全部」 */
  selectedCategory: string
}

export const useFoodStore = defineStore('food', {
  state: (): FoodState => ({
    foods: [],
    categories: [],
    loading: false,
    error: '',
    searchKeyword: '',
    selectedCategory: ALL_CATEGORY_CODE,
  }),

  getters: {
    /**
     * 搜索关键词与分类共同作用后的食品列表。
     * 数据量小且要求即时响应，因此筛选在前端完成，不额外增加接口。
     */
    filteredFoods(state): FoodSummary[] {
      const keyword = state.searchKeyword.trim().toLowerCase()

      return state.foods.filter((food) => {
        const matchesCategory =
          state.selectedCategory === ALL_CATEGORY_CODE || food.categoryCode === state.selectedCategory
        const matchesKeyword = !keyword || food.name.toLowerCase().includes(keyword)

        return matchesCategory && matchesKeyword
      })
    },

    /** 在真实分类前拼一个「全部」选项，筛选组件可直接渲染 */
    categoryOptions(state): CategoryOption[] {
      return [{ code: ALL_CATEGORY_CODE, name: '全部', sortOrder: 0 }, ...state.categories]
    },
  },

  actions: {
    /** 并发拉取分类与食物列表；任一步失败都给出统一的可读提示 */
    async loadCatalog() {
      this.loading = true
      this.error = ''

      try {
        const [categories, foods] = await Promise.all([fetchCategories(), fetchFoods()])
        this.categories = categories
        this.foods = foods
      } catch (err) {
        this.error = err instanceof Error ? err.message : '数据加载失败，请稍后重试'
      } finally {
        this.loading = false
      }
    },

    setSearchKeyword(keyword: string) {
      this.searchKeyword = keyword
    },

    setCategory(code: string) {
      this.selectedCategory = code
    },

    resetFilters() {
      this.searchKeyword = ''
      this.selectedCategory = ALL_CATEGORY_CODE
    },

    /** 从已加载列表中按 ID 查找；找不到返回 null，由调用方决定展示什么 */
    foodById(id: number): FoodSummary | null {
      return this.foods.find((food) => food.id === id) ?? null
    },
  },
})