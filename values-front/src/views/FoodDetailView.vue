<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import {
  ArrowLeft,
  ChevronRight,
  Database,
  ExternalLink,
  Info,
  LoaderCircle,
  TriangleAlert,
} from 'lucide-vue-next'
import { fetchFoodDetail } from '@/services/food'
import { HttpError } from '@/services/http'
import { FOOD_DATA_CENTRAL_URL, NUTRIENT_RULE_URL } from '@/constants/external-links'
import type { FoodDetail } from '@/types/food'
import { categoryTone } from '@/utils/category-tone'
import { nutrientTone } from '@/utils/nutrient-tone'
import { handleFoodImageError } from '@/utils/image'

const route = useRoute()

/** 所有营养数值统一按「每 100g 可食部分」展示；这是固定口径，仅作展示文案 */
const NUTRIENT_BASIS = '每 100g 可食部分'

const food = ref<FoodDetail | null>(null)
const loading = ref(false)
const error = ref('')
// 404 单独标记，用于区分「资源不存在」与「请求失败」两种状态，二者提示与操作不同
const notFound = ref(false)

const tone = computed(() => (food.value ? categoryTone(food.value.categoryCode) : ''))

/** 热量块的数值取自营养卡片中 code 为 ENERGY 的那项，避免在页面里重复硬编码热量 */
const energyTile = computed(
  () => food.value?.nutrientTiles.find((item) => item.code === 'ENERGY') ?? null,
)

async function loadDetail() {
  const id = Number(route.params.id)

  // 非整数的路由参数不请求后端，直接按未找到处理，省去一次必然 404 的往返
  if (!Number.isInteger(id)) {
    food.value = null
    error.value = ''
    notFound.value = true
    loading.value = false
    return
  }

  loading.value = true
  error.value = ''
  notFound.value = false

  try {
    food.value = await fetchFoodDetail(id)
  } catch (err) {
    food.value = null
    if (err instanceof HttpError && err.status === 404) {
      notFound.value = true
    } else {
      error.value = err instanceof Error ? err.message : '详情加载失败，请稍后重试'
    }
  } finally {
    loading.value = false
  }
}

// 监听路由参数：首次进入立即加载，切换食物时重新拉取
watch(() => route.params.id, loadDetail, { immediate: true })
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
            :src="food.imageUrl"
            :alt="food.name"
            width="176"
            height="176"
            @error="handleFoodImageError"
          />
        </div>

        <div class="detail-hero__body">
          <div class="detail-hero__badges">
            <span class="category-tag" :class="tone">{{ food.categoryName }}</span>
            <span class="state-badge">{{ food.state }}</span>
            <span v-if="!food.source.verified" class="state-badge state-badge--pending">待校验</span>
          </div>

          <h1 class="detail-hero__name">{{ food.name }}</h1>
          <p class="detail-hero__desc">{{ food.description }}</p>

          <p class="detail-hero__meta">
            <span>示例数据 · {{ NUTRIENT_BASIS }}</span>
            <span aria-hidden="true">·</span>
            <span>
              {{ food.source.name }}
              <template v-if="food.source.recordId"> · FDC ID {{ food.source.recordId }}</template>
            </span>
          </p>

          <div class="detail-energy">
            <span class="detail-energy__value">{{ energyTile?.amount }}</span>
            <span class="detail-energy__unit">{{ energyTile?.unit }}</span>
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
                <p>{{ NUTRIENT_BASIS }} · NRV% 依据 {{ food.ruleStandard.name }} 附录 A</p>
              </div>
              <span class="data-status" :class="{ 'is-verified': food.source.verified }">
                {{ food.source.verified ? '已标注来源' : '待校验' }}
              </span>
            </div>

            <div class="nutrient-tiles">
              <div
                v-for="item in food.nutrientTiles"
                :key="item.code"
                class="nutrient-tile"
                :class="nutrientTone(item.code)"
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
              <span v-if="food.highlights.length" class="data-status is-verified">
                {{ food.highlights.length }} 项达标
              </span>
            </div>

            <div v-if="food.highlights.length" class="knowledge-grid">
              <article v-for="item in food.highlights" :key="item.code" class="knowledge-card">
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
                <dd>{{ food.source.name }}</dd>
              </div>
              <div v-if="food.source.recordId">
                <dt>记录 ID</dt>
                <dd>FDC {{ food.source.recordId }}</dd>
              </div>
            </dl>

            <a
              class="source-link"
              :href="FOOD_DATA_CENTRAL_URL"
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
              营养亮点按 {{ food.ruleStandard.name }} 的判定口径筛选：维生素、矿物质每 100g 达到
              ≥30% NRV，蛋白质每 100g ≥12g，膳食纤维每 100g ≥6g。
            </p>
            <p>
              未达到条件的营养素不列为亮点，其原始含量仍保留在营养成分表中；钠、饱和脂肪等需要特别处理的成分，本页不作为营养亮点展示。
            </p>
            <p v-if="food.claimNote">{{ food.claimNote }}</p>
            <a
              class="source-link"
              :href="NUTRIENT_RULE_URL"
              target="_blank"
              rel="noopener noreferrer"
            >
              查看{{ food.ruleStandard.name }}问答
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

    <div v-else-if="loading" class="food-empty">
      <div class="food-empty__icon">
        <LoaderCircle aria-hidden="true" />
      </div>
      <h3>正在加载食物详情</h3>
      <p>请稍候……</p>
    </div>

    <div v-else-if="error" class="food-empty">
      <div class="food-empty__icon">
        <TriangleAlert aria-hidden="true" />
      </div>
      <h3>加载失败</h3>
      <p>{{ error }}</p>
      <button type="button" @click="loadDetail">重新加载</button>
    </div>

    <div v-else-if="notFound" class="food-empty">
      <h3>未找到该食物</h3>
      <p>它可能已被移除，或链接地址不正确</p>
      <RouterLink to="/foods" class="empty-link">返回食物百科</RouterLink>
    </div>
  </div>
</template>