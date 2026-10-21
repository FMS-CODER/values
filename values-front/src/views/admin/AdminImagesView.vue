<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import {
  Check,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  Images,
  LoaderCircle,
  Search,
  TriangleAlert,
  X,
} from 'lucide-vue-next'
import { fetchAdminImages, reviewImage } from '@/services/admin'
import type { AdminImageItem, ReviewStatus } from '@/types/admin'
import { handleFoodImageError, resolveFoodImage } from '@/utils/image'

/** 与后端约定每页 24 条 */
const SIZE = 24

const STATUS_TABS: { value: ReviewStatus | 'all'; label: string }[] = [
  { value: 'pending', label: '待审核' },
  { value: 'approved', label: '已通过' },
  { value: 'rejected', label: '已驳回' },
  { value: 'all', label: '全部' },
]

const STATUS_LABELS: Record<ReviewStatus, string> = {
  pending: '待审核',
  approved: '已通过',
  rejected: '已驳回',
}

const status = ref<ReviewStatus | 'all'>('pending')
const keywordInput = ref('')
const appliedKeyword = ref('')
const page = ref(1)
const items = ref<AdminImageItem[]>([])
const total = ref(0)
const totalPages = ref(0)
const pageCount = computed(() => Math.max(totalPages.value, 1))

const loading = ref(false)
const error = ref('')
const actionError = ref('')
/** 接口用 hint 说明图片清单缺失，需要先跑 Python 脚本，属于提示而非错误 */
const hint = ref('')

const notice = ref('')
let noticeTimer: number | undefined

function flash(message: string) {
  notice.value = message
  if (noticeTimer) window.clearTimeout(noticeTimer)
  noticeTimer = window.setTimeout(() => {
    notice.value = ''
  }, 3000)
}

function statusLabel(value: ReviewStatus): string {
  return STATUS_LABELS[value] ?? value
}

async function loadImages() {
  loading.value = true
  error.value = ''

  try {
    const data = await fetchAdminImages({
      status: status.value,
      keyword: appliedKeyword.value,
      page: page.value,
      size: SIZE,
    })
    items.value = data.items
    total.value = data.total
    totalPages.value = data.totalPages
    hint.value = data.hint ?? ''
    page.value = data.page
  } catch (err) {
    items.value = []
    total.value = 0
    totalPages.value = 0
    error.value = err instanceof Error ? err.message : '图片列表加载失败'
  } finally {
    loading.value = false
  }
}

function switchStatus(next: ReviewStatus | 'all') {
  if (status.value === next) return
  status.value = next
  page.value = 1
  loadImages()
}

function submitSearch() {
  appliedKeyword.value = keywordInput.value.trim()
  page.value = 1
  loadImages()
}

function goPage(target: number) {
  if (target < 1 || target > totalPages.value || target === page.value || loading.value) return
  page.value = target
  loadImages()
}

/* ---------- 审核操作 ---------- */

const actingId = ref<number | null>(null)

async function review(item: AdminImageItem, next: Extract<ReviewStatus, 'approved' | 'rejected'>) {
  if (actingId.value !== null) return

  actionError.value = ''
  actingId.value = item.foodId
  try {
    const updated = await reviewImage(item.foodId, next)
    // 后端返回同结构 item，原地替换这一张卡片即可，整页刷新会让审核过程不停闪烁
    const index = items.value.findIndex((entry) => entry.foodId === item.foodId)
    if (index >= 0) items.value[index] = updated
    flash(next === 'approved' ? '已标记为通过' : '已标记为驳回')
  } catch (err) {
    actionError.value = err instanceof Error ? err.message : '操作失败，请稍后重试'
  } finally {
    actingId.value = null
  }
}

onMounted(loadImages)

onUnmounted(() => {
  if (noticeTimer) window.clearTimeout(noticeTimer)
})
</script>

<template>
  <section class="admin-panel">
    <div class="admin-toolbar">
      <div class="admin-tabs" role="group" aria-label="按审核状态筛选">
        <button
          v-for="tab in STATUS_TABS"
          :key="tab.value"
          type="button"
          class="admin-tab"
          :class="{ 'is-active': status === tab.value }"
          :aria-pressed="status === tab.value"
          @click="switchStatus(tab.value)"
        >
          {{ tab.label }}
        </button>
      </div>

      <form class="admin-search admin-toolbar__spacer" role="search" @submit.prevent="submitSearch">
        <Search aria-hidden="true" />
        <input
          v-model="keywordInput"
          type="search"
          placeholder="搜索食物名称"
          aria-label="搜索食物名称"
        />
      </form>
      <button type="button" class="admin-button" @click="submitSearch">搜索</button>
    </div>

    <p v-if="hint" class="admin-alert admin-alert--panel">{{ hint }}</p>
    <p v-if="notice" class="admin-alert admin-alert--success admin-alert--panel">{{ notice }}</p>
    <p v-if="actionError" class="admin-alert admin-alert--error admin-alert--panel">{{ actionError }}</p>

    <div v-if="loading" class="admin-state">
      <LoaderCircle class="admin-spin" aria-hidden="true" />
      <h3>正在加载图片</h3>
      <p>请稍候……</p>
    </div>

    <div v-else-if="error" class="admin-state">
      <TriangleAlert aria-hidden="true" />
      <h3>加载失败</h3>
      <p>{{ error }}</p>
      <button type="button" class="admin-button" @click="loadImages">重新加载</button>
    </div>

    <div v-else-if="!items.length" class="admin-state">
      <Images aria-hidden="true" />
      <h3>没有符合条件的图片</h3>
      <p>切换状态或更换关键词再看看</p>
    </div>

    <template v-else>
      <div class="admin-image-grid">
        <article v-for="item in items" :key="item.foodId" class="admin-image-card">
          <div class="admin-image-card__media">
            <!-- 下方已有食物名，图片按装饰处理，空 alt 避免读屏重复 -->
            <img :src="resolveFoodImage(item.imageUrl)" alt="" @error="handleFoodImageError" />
          </div>

          <div class="admin-image-card__body">
            <div class="admin-image-card__head">
              <div class="admin-image-card__title">
                <div class="admin-image-card__name">{{ item.foodName }}</div>
                <div class="admin-image-card__id">食物 ID {{ item.foodId }}</div>
              </div>
              <span class="admin-badge" :class="`admin-badge--${item.reviewStatus}`">
                {{ statusLabel(item.reviewStatus) }}
              </span>
            </div>

            <dl class="admin-image-card__meta">
              <div>
                <dt>搜索来源</dt>
                <dd>{{ item.sourceName ?? '—' }}</dd>
              </div>
              <div>
                <dt>许可</dt>
                <dd>{{ item.license ?? '—' }}</dd>
              </div>
              <div>
                <dt>作者</dt>
                <dd>{{ item.photographer ?? '—' }}</dd>
              </div>
            </dl>

            <a
              v-if="item.sourceUrl"
              class="admin-image-card__link"
              :href="item.sourceUrl"
              target="_blank"
              rel="noopener noreferrer"
            >
              <ExternalLink aria-hidden="true" />
              <span>来源页面</span>
            </a>

            <div class="admin-image-card__actions">
              <button
                type="button"
                class="admin-button admin-button--sm admin-button--success"
                :disabled="actingId !== null || item.reviewStatus === 'approved'"
                @click="review(item, 'approved')"
              >
                <Check aria-hidden="true" />
                <span>通过</span>
              </button>
              <button
                type="button"
                class="admin-button admin-button--sm admin-button--danger"
                :disabled="actingId !== null || item.reviewStatus === 'rejected'"
                @click="review(item, 'rejected')"
              >
                <X aria-hidden="true" />
                <span>驳回</span>
              </button>
            </div>
          </div>
        </article>
      </div>

      <div class="admin-pagination">
        <span class="admin-pagination__info">第 {{ page }} / {{ pageCount }} 页，共 {{ total }} 条</span>
        <div class="admin-pagination__actions">
          <button
            type="button"
            class="admin-button admin-button--sm"
            :disabled="page <= 1 || loading"
            @click="goPage(page - 1)"
          >
            <ChevronLeft aria-hidden="true" />
            <span>上一页</span>
          </button>
          <button
            type="button"
            class="admin-button admin-button--sm"
            :disabled="page >= totalPages || loading"
            @click="goPage(page + 1)"
          >
            <span>下一页</span>
            <ChevronRight aria-hidden="true" />
          </button>
        </div>
      </div>
    </template>
  </section>
</template>