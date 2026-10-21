<script setup lang="ts">
import { storeToRefs } from 'pinia'
import { SearchX } from 'lucide-vue-next'
import FoodCard from '@/components/FoodCard.vue'
import { useFoodStore } from '@/stores/food'

const store = useFoodStore()
const { filteredFoods, searchKeyword, selectedCategory } = storeToRefs(store)

function resetFilters() {
  store.resetFilters()
}
</script>

<template>
  <div v-if="filteredFoods.length" class="food-grid">
    <FoodCard v-for="food in filteredFoods" :key="food.id" :food="food" />
  </div>

  <div v-else class="food-empty">
    <div class="food-empty__icon">
      <SearchX aria-hidden="true" />
    </div>
    <h3>没有找到相关食物</h3>
    <p>请尝试其他关键词，或切换一个分类看看</p>
    <button
      v-if="searchKeyword || selectedCategory !== '全部'"
      type="button"
      @click="resetFilters"
    >
      清空筛选条件
    </button>
  </div>
</template>
