<script setup lang="ts">
import FoodHero from '@/components/FoodHero.vue'
import FoodCategoryFilter from '@/components/FoodCategoryFilter.vue'
import FoodGrid from '@/components/FoodGrid.vue'
</script>

<template>
  <div class="page">
    <FoodHero />
    <FoodCategoryFilter />
    <FoodGrid />
  </div>
</template>
