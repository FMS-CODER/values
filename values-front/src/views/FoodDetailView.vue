<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { ArrowLeft, ChevronRight, Database, ExternalLink, Info } from 'lucide-vue-next'
import { CATEGORY_TONES } from '@/data/foods'
import {
  getFoodHighlights,
  getNrvPercent,
  getNutrientAmount,
  NUTRIENT_BASIS,
  NUTRIENT_CODES,
  NUTRIENT_INFO,
  RICH_RULE_SOURCE,
} from '@/data/nutrients'
import { useFoodStore } from '@/stores/food'
import { handleFoodImageError } from '@/utils/image'

const route = useRoute()
const store = useFoodStore()

// 路由参数来自地址栏，可能不是有效数字；无效时 getter 返回 null 并展示未找到状态
const food = computed(() => store.foodById(Number(route.params.id)))
const categoryTone = computed(() => (food.value ? CATEGORY_TONES[food.value.category] : ''))

/** 详情页按营养素基础表的固定顺序生成全部含量卡片，并附带 NRV% */
const nutrientTiles = computed(() => {
  const currentFood = food.value
  if (!currentFood) return []

  return NUTRIENT_CODES.map((code) => ({
    code,
    ...NUTRIENT_INFO[code],
    amount: getNutrientAmount(currentFood.id, code),
    nrvPercent: getNrvPercent(currentFood.id, code),
  }))
})

/**
 * 营养亮点。
 * 达标判定放在数据层完成，页面只负责渲染结果；
 * 未达标的营养素不出现在这里，但仍保留在上方营养成分表中。
 */
const highlights = computed(() => (food.value ? getFoodHighlights(food.value.id) : []))
</script>

<template>
  <div class="page detail-page">
    <template v-if="food">
      <nav class="detail-breadcrumb" aria-label="面包屑">
        <RouterLink to="/foods">食物百科</RouterLink>
        <ChevronRight aria-hidden="true" />
        <span>{{ food.name }}</span>
      </nav>

      <section class="detail-hero">
        <div class="detail-hero__media">
          <img
            class="detail-hero__image"
            :src="food.image"
            :alt="food.name"
            width="176"
            height="176"
            @error="handleFoodImageError"
          />
        </div>

        <div class="detail-hero__body">
          <div class="detail-hero__badges">
            <span class="category-tag" :class="categoryTone">{{ food.category }}</span>
            <span class="state-badge">{{ food.state }}</span>
            <span v-if="!food.source.verified" class="state-badge state-badge--pending">待校验</span>
          </div>

          <h1 class="detail-hero__name">{{ food.name }}</h1>
          <p class="detail-hero__desc">{{ food.description }}</p>

          <p class="detail-hero__meta">
            <span>示例数据 · {{ NUTRIENT_BASIS }}</span>
            <span aria-hidden="true">·</span>
            <span>
              {{ food.source.label }}
              <template v-if="food.source.recordId"> · FDC ID {{ food.source.recordId }}</template>
            </span>
          </p>

          <div class="detail-energy">
            <span class="detail-energy__value">{{ getNutrientAmount(food.id, 'calories') }}</span>
            <span class="detail-energy__unit">kcal</span>
            <span class="detail-energy__label">每 100g 热量</span>
          </div>
        </div>
      </section>

      <div class="detail-layout">
        <div class="detail-main">
          <section class="detail-section">
            <div class="detail-section__head">
              <div>
                <h2>每 100g 营养成分</h2>
                <p>{{ NUTRIENT_BASIS }} · NRV% 依据 {{ RICH_RULE_SOURCE.label }} 附录 A</p>
              </div>
              <span class="data-status" :class="{ 'is-verified': food.source.verified }">
                {{ food.source.verified ? '已标注来源' : '待校验' }}
              </span>
            </div>

            <div class="nutrient-tiles">
              <div
                v-for="item in nutrientTiles"
                :key="item.code"
                class="nutrient-tile"
                :class="item.tone"
              >
                <p class="nutrient-tile__name">{{ item.name }}</p>
                <p class="nutrient-tile__value">
                  {{ item.amount }}<span>{{ item.unit }}</span>
                </p>
                <p class="nutrient-tile__nrv">
                  {{ item.nrvPercent === null ? '无 NRV' : `NRV ${item.nrvPercent}%` }}
                </p>
              </div>
            </div>
          </section>

          <section class="detail-section">
            <div class="detail-section__head">
              <div>
                <h2>营养亮点</h2>
                <p>仅列出达到「富含」判定条件的营养素</p>
              </div>
              <span v-if="highlights.length" class="data-status is-verified">
                {{ highlights.length }} 项达标
              </span>
            </div>

            <div v-if="highlights.length" class="knowledge-grid">
              <article v-for="item in highlights" :key="item.code" class="knowledge-card">
                <div class="knowledge-card__head">
                  <h3>{{ item.name }}</h3>
                  <span class="knowledge-card__amount">{{ item.amount }} {{ item.unit }}</span>
                </div>

                <p class="knowledge-card__rule">
                  <span class="rich-badge">富含</span>
                  {{ item.ruleLabel }}
                  <template v-if="item.nrvPercent !== null"> · NRV {{ item.nrvPercent }}%</template>
                </p>

                <p class="knowledge-card__role">{{ item.role }}</p>

                <div class="knowledge-card__meta">
                  <a :href="item.sourceUrl" target="_blank" rel="noopener noreferrer">
                    {{ item.sourceName }}
                    <ExternalLink aria-hidden="true" />
                  </a>
                  <span>核验 {{ item.verifiedAt }}</span>
                </div>
              </article>
            </div>

            <p v-else class="knowledge-empty">
              {{ food.name }}没有达到「富含」判定条件的营养素，因此不列出营养亮点；各项原始含量仍完整保留在上方营养成分表中。
            </p>
          </section>
        </div>

        <aside class="detail-aside">
          <section class="info-card">
            <h2 class="info-card__title">
              <Database aria-hidden="true" />
              数据来源
            </h2>
            <dl class="source-list">
              <div>
                <dt>计量基准</dt>
                <dd>{{ NUTRIENT_BASIS }}</dd>
              </div>
              <div>
                <dt>食品状态</dt>
                <dd>{{ food.state }}</dd>
              </div>
              <div>
                <dt>数据来源</dt>
                <dd>{{ food.source.label }}</dd>
              </div>
              <div v-if="food.source.recordId">
                <dt>记录 ID</dt>
                <dd>FDC {{ food.source.recordId }}</dd>
              </div>
            </dl>

            <a
              v-if="food.source.url"
              class="source-link"
              :href="food.source.url"
              target="_blank"
              rel="noopener noreferrer"
            >
              前往 FoodData Central 检索
              <ExternalLink aria-hidden="true" />
            </a>

            <p class="info-card__note">{{ food.source.note }}</p>
          </section>

          <section class="info-card info-card--claim">
            <h2 class="info-card__title">
              <Info aria-hidden="true" />
              关于营养声称
            </h2>
            <p>
              营养亮点按 {{ RICH_RULE_SOURCE.label }} 的判定口径筛选：维生素、矿物质每 100g 达到
              ≥30% NRV，蛋白质每 100g ≥12g，膳食纤维每 100g ≥6g。
            </p>
            <p>
              未达到条件的营养素不列为亮点，其原始含量仍保留在营养成分表中；钠、饱和脂肪等需要特别处理的成分，本页不作为营养亮点展示。
            </p>
            <p v-if="food.claimNote">{{ food.claimNote }}</p>
            <a
              class="source-link"
              :href="RICH_RULE_SOURCE.url"
              target="_blank"
              rel="noopener noreferrer"
            >
              查看{{ RICH_RULE_SOURCE.label }}问答
              <ExternalLink aria-hidden="true" />
            </a>
          </section>

          <RouterLink to="/foods" class="detail-back">
            <ArrowLeft aria-hidden="true" />
            返回食物百科
          </RouterLink>
        </aside>
      </div>
    </template>

    <div v-else class="food-empty">
      <h3>未找到该食物</h3>
      <p>它可能已被移除，或链接地址不正确</p>
      <RouterLink to="/foods" class="empty-link">返回食物百科</RouterLink>
    </div>
  </div>
</template>
