<script setup lang="ts">
import { storeToRefs } from 'pinia'
import { useFoodStore } from '@/stores/food'

const store = useFoodStore()
const { selectedCategory, categoryOptions } = storeToRefs(store)
</script>

<template>
  <div class="category-filter" role="group" aria-label="食物分类筛选">
    <button
      v-for="category in categoryOptions"
      :key="category.code"
      type="button"
      class="category-chip"
      :class="{ 'is-active': selectedCategory === category.code }"
      :aria-pressed="selectedCategory === category.code"
      @click="store.setCategory(category.code)"
    >
      {{ category.name }}
    </button>
  </div>
</template>