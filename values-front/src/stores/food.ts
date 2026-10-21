import { defineStore } from 'pinia'
import { foods, type CategoryFilter, type Food } from '@/data/foods'

interface FoodState {
  foods: Food[]
  searchKeyword: string
  selectedCategory: CategoryFilter
}

export const useFoodStore = defineStore('food', {
  state: (): FoodState => ({
    foods,
    searchKeyword: '',
    selectedCategory: '全部',
  }),

  getters: {
    /** 搜索关键词与分类共同作用后的食品列表 */
    filteredFoods(state): Food[] {
      const keyword = state.searchKeyword.trim().toLowerCase()

      return state.foods.filter((food) => {
        const matchesCategory =
          state.selectedCategory === '全部' || food.category === state.selectedCategory
        const matchesKeyword = !keyword || food.name.toLowerCase().includes(keyword)

        return matchesCategory && matchesKeyword
      })
    },

    /**
     * 按 ID 查询食物，供详情页复用。
     * 返回函数形式以便 getter 接收参数；无效 ID 返回 null，由页面展示未找到状态。
     */
    foodById(state) {
      return (id: number): Food | null =>
        state.foods.find((food) => food.id === id) ?? null
    },
  },

  actions: {
    setSearchKeyword(keyword: string) {
      this.searchKeyword = keyword
    },

    setCategory(category: CategoryFilter) {
      this.selectedCategory = category
    },

    resetFilters() {
      this.searchKeyword = ''
      this.selectedCategory = '全部'
    },
  },
})
