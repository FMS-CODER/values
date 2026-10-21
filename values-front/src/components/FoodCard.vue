<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { ArrowRight } from 'lucide-vue-next'
import type { FoodSummary } from '@/types/food'
import { categoryTone } from '@/utils/category-tone'
import { nutrientTone } from '@/utils/nutrient-tone'
import { handleFoodImageError } from '@/utils/image'

const props = defineProps<{ food: FoodSummary }>()

const tone = computed(() => categoryTone(props.food.categoryCode))
</script>

<template>
  <article class="food-card">
    <div class="food-card__media">
      <img
        class="food-card__image"
        :src="food.imageUrl"
        :alt="food.name"
        loading="lazy"
        decoding="async"
        width="128"
        height="128"
        @error="handleFoodImageError"
      />
    </div>

    <div class="food-card__body">
      <div class="food-card__head">
        <h3 class="food-card__name">{{ food.name }}</h3>
        <span class="category-tag" :class="tone">{{ food.categoryName }}</span>
      </div>

      <p class="food-card__desc">{{ food.description }}</p>

      <div class="food-card__nutrition">
        <p class="nutrition-caption">每 100g 营养成分</p>
        <!-- 卡片只展示后端返回的 nutrients，完整营养构成在详情页呈现 -->
        <div class="nutrition-grid">
          <div
            v-for="item in food.nutrients"
            :key="item.code"
            class="nutrition-item"
            :class="nutrientTone(item.code)"
          >
            <p class="nutrition-item__label">{{ item.name }}</p>
            <p class="nutrition-item__value">
              {{ item.amount }}<span class="nutrition-item__unit">{{ item.unit }}</span>
            </p>
          </div>
        </div>
      </div>

      <div class="food-card__footer">
        <RouterLink
          :to="{ name: 'food-detail', params: { id: food.id } }"
          class="detail-link"
          :aria-label="`查看${food.name}详情`"
        >
          查看详情
          <ArrowRight aria-hidden="true" />
        </RouterLink>
      </div>
    </div>
  </article>
</template>