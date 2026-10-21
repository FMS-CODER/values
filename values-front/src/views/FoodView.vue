<script setup lang="ts">
import FoodCategoryFilter from '@/components/FoodCategoryFilter.vue'
import FoodGrid from '@/components/FoodGrid.vue'
</script>

<template>
  <div class="page">
    <div class="page-heading">
      <h1>食物百科</h1>
      <p>浏览常见食材，了解它们每 100g 的营养构成。</p>
    </div>

    <FoodCategoryFilter />
    <FoodGrid />
  </div>
</template>
