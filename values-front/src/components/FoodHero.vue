<script setup lang="ts">
import { handleFoodImageError } from '@/utils/image'
</script>

<template>
  <section class="food-hero">
    <div class="food-hero__content">
      <h1 class="food-hero__title">探索食物的营养价值</h1>
      <p class="food-hero__subtitle">
        从蔬菜到水果，从主食到肉类，了解每一种食物的营养成分，让健康饮食更简单。
      </p>
    </div>

    <div class="food-hero__visual" aria-hidden="true">
      <img
        class="food-hero__image food-hero__image--main"
        src="/foods/broccoli.jpg"
        alt=""
        @error="handleFoodImageError"
      />
      <img
        class="food-hero__image food-hero__image--small"
        src="/foods/apple.jpg"
        alt=""
        @error="handleFoodImageError"
      />
      <img
        class="food-hero__image food-hero__image--tiny"
        src="/foods/almond.jpg"
        alt=""
        @error="handleFoodImageError"
      />
    </div>
  </section>
</template>
