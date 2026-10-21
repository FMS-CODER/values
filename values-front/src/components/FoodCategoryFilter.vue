<script setup lang="ts">
import { storeToRefs } from 'pinia'
import { CATEGORIES } from '@/data/foods'
import { useFoodStore } from '@/stores/food'

const store = useFoodStore()
const { selectedCategory } = storeToRefs(store)
</script>

<template>
  <div class="category-filter" role="group" aria-label="食物分类筛选">
    <button
      v-for="category in CATEGORIES"
      :key="category"
      type="button"
      class="category-chip"
      :class="{ 'is-active': selectedCategory === category }"
      :aria-pressed="selectedCategory === category"
      @click="store.setCategory(category)"
    >
      {{ category }}
    </button>
  </div>
</template>
