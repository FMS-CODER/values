<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { ArrowRight } from 'lucide-vue-next'
import type { FoodSummary } from '@/types/food'
import { categoryTone } from '@/utils/category-tone'
import { nutrientTone } from '@/utils/nutrient-tone'
import { handleFoodImageError, resolveFoodImage } from '@/utils/image'

const props = defineProps<{ food: FoodSummary }>()

const tone = computed(() => categoryTone(props.food.categoryCode))

// 图片地址可能为 null，这里统一解析成占位图，避免模板里出现 src=""
const imageSrc = computed(() => resolveFoodImage(props.food.imageUrl))
</script>

<template>
  <article class="food-card">
    <div class="food-card__media">
      <img
        class="food-card__image"
        :src="imageSrc"
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

      <!-- 介绍可能为 null，为空时整行不渲染，避免留下空白行影响卡片高度 -->
      <p v-if="food.description" class="food-card__desc">{{ food.description }}</p>

      <div class="food-card__nutrition">
        <p class="nutrition-caption">每 100g 营养成分</p>
        <!-- 接口固定返回 4 个槽位，即使某项缺失也照常占位，保持四列对齐 -->
        <div class="nutrition-grid">
          <div
            v-for="item in food.nutrients"
            :key="item.code"
            class="nutrition-item"
            :class="nutrientTone(item.code)"
          >
            <p class="nutrition-item__label">{{ item.name }}</p>
            <!-- 缺失值用「—」占位，与 0 区分，同时不显示单位 -->
            <p class="nutrition-item__value">
              <template v-if="item.amount === null">—</template>
              <template v-else>
                {{ item.amount }}<span class="nutrition-item__unit">{{ item.unit }}</span>
              </template>
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