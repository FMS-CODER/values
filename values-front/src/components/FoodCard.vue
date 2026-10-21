<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { ArrowRight } from 'lucide-vue-next'
import { CATEGORY_TONES, type Food } from '@/data/foods'
import { getNutrientAmount, NUTRIENT_INFO, type NutrientCode } from '@/data/nutrients'
import { handleFoodImageError } from '@/utils/image'

const props = defineProps<{ food: Food }>()

const categoryTone = computed(() => CATEGORY_TONES[props.food.category])

/** 列表卡片只展示四项基础数据，完整营养构成在详情页呈现 */
const CARD_NUTRIENTS: NutrientCode[] = ['calories', 'protein', 'fat', 'carbohydrates']

const nutritionItems = computed(() =>
  CARD_NUTRIENTS.map((code) => {
    const info = NUTRIENT_INFO[code]
    return {
      label: info.name,
      value: getNutrientAmount(props.food.id, code),
      unit: info.unit,
      tone: info.tone,
    }
  }),
)
</script>

<template>
  <article class="food-card">
    <div class="food-card__media">
      <img
        class="food-card__image"
        :src="food.image"
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
        <span class="category-tag" :class="categoryTone">{{ food.category }}</span>
      </div>

      <p class="food-card__desc">{{ food.description }}</p>

      <div class="food-card__nutrition">
        <p class="nutrition-caption">每 100g 营养成分</p>
        <div class="nutrition-grid">
          <div
            v-for="item in nutritionItems"
            :key="item.label"
            class="nutrition-item"
            :class="item.tone"
          >
            <p class="nutrition-item__label">{{ item.label }}</p>
            <p class="nutrition-item__value">
              {{ item.value }}<span class="nutrition-item__unit">{{ item.unit }}</span>
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
