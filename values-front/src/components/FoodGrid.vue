<script setup lang="ts">
import { storeToRefs } from 'pinia'
import { LoaderCircle, SearchX, TriangleAlert } from 'lucide-vue-next'
import FoodCard from '@/components/FoodCard.vue'
import { ALL_CATEGORY_CODE, useFoodStore } from '@/stores/food'

const store = useFoodStore()
const { filteredFoods, searchKeyword, selectedCategory, loading, error } = storeToRefs(store)

function resetFilters() {
  store.resetFilters()
}

function reload() {
  store.loadCatalog()
}
</script>

<template>
  <!-- 加载中优先于空状态，避免数据未就绪时误报「没有找到相关食物」 -->
  <div v-if="loading" class="food-empty">
    <div class="food-empty__icon">
      <LoaderCircle aria-hidden="true" />
    </div>
    <h3>正在加载食物列表</h3>
    <p>请稍候……</p>
  </div>

  <div v-else-if="error" class="food-empty">
    <div class="food-empty__icon">
      <TriangleAlert aria-hidden="true" />
    </div>
    <h3>加载失败</h3>
    <p>{{ error }}</p>
    <button type="button" @click="reload">重新加载</button>
  </div>

  <div v-else-if="filteredFoods.length" class="food-grid">
    <FoodCard v-for="food in filteredFoods" :key="food.id" :food="food" />
  </div>

  <div v-else class="food-empty">
    <div class="food-empty__icon">
      <SearchX aria-hidden="true" />
    </div>
    <h3>没有找到相关食物</h3>
    <p>请尝试其他关键词，或切换一个分类看看</p>
    <button
      v-if="searchKeyword || selectedCategory !== ALL_CATEGORY_CODE"
      type="button"
      @click="resetFilters"
    >
      清空筛选条件
    </button>
  </div>
</template>