<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import {
  ChevronLeft,
  ChevronRight,
  LoaderCircle,
  Pencil,
  Plus,
  Search,
  SearchX,
  Trash2,
  TriangleAlert,
  X,
} from 'lucide-vue-next'
import {
  createFood,
  deleteFood,
  fetchAdminCategories,
  fetchAdminFood,
  fetchAdminFoods,
  updateFood,
} from '@/services/admin'
import type { AdminCategory, AdminFoodForm, AdminFoodListItem } from '@/types/admin'
import { categoryTone } from '@/utils/category-tone'
import { handleFoodImageError, resolveFoodImage } from '@/utils/image'

/** 与后端约定每页 20 条 */
const SIZE = 20

const items = ref<AdminFoodListItem[]>([])
const total = ref(0)
const totalPages = ref(0)
const page = ref(1)
const pageCount = computed(() => Math.max(totalPages.value, 1))

const loading = ref(false)
const error = ref('')
/** 删除等操作的错误单独展示，避免把已经加载好的表格整个换成错误态 */
const actionError = ref('')

const keywordInput = ref('')
const appliedKeyword = ref('')
const categoryCode = ref('')
const categories = ref<AdminCategory[]>([])
const categoriesError = ref('')

async function loadCategories() {
  categoriesError.value = ''
  try {
    categories.value = await fetchAdminCategories()
  } catch (err) {
    categoriesError.value = err instanceof Error ? err.message : '分类列表加载失败'
  }
}

async function loadFoods() {
  loading.value = true
  error.value = ''

  try {
    const data = await fetchAdminFoods({
      keyword: appliedKeyword.value,
      categoryCode: categoryCode.value,
      page: page.value,
      size: SIZE,
    })
    items.value = data.items
    total.value = data.total
    totalPages.value = data.totalPages
    // 后端可能把越界页码修正到有效范围，以响应为准可以避免分页显示与实际数据错位
    page.value = data.page
  } catch (err) {
    error.value = err instanceof Error ? err.message : '食物列表加载失败'
  } finally {
    loading.value = false
  }
}

function submitSearch() {
  appliedKeyword.value = keywordInput.value.trim()
  page.value = 1
  loadFoods()
}

function changeCategory() {
  page.value = 1
  loadFoods()
}

function clearFilters() {
  keywordInput.value = ''
  appliedKeyword.value = ''
  categoryCode.value = ''
  page.value = 1
  loadFoods()
}

function goPage(target: number) {
  if (target < 1 || target > totalPages.value || target === page.value || loading.value) return
  page.value = target
  loadFoods()
}

function formatTime(value: string): string {
  // 后端返回 ISO 时间串，管理端只需要「到分钟」的可读形式
  if (!value) return '—'
  return value.replace('T', ' ').slice(0, 16)
}

/* ---------- 新增 / 编辑弹窗 ---------- */

interface FoodFormState {
  name: string
  nameEn: string
  categoryId: string
  imageUrl: string
  description: string
  state: string
  fdcId: string
  verified: boolean
  sourceNote: string
  claimNote: string
}

function emptyFoodForm(): FoodFormState {
  return {
    name: '',
    nameEn: '',
    categoryId: '',
    imageUrl: '',
    description: '',
    state: '',
    fdcId: '',
    verified: false,
    sourceNote: '',
    claimNote: '',
  }
}

const modalOpen = ref(false)
const editingId = ref<number | null>(null)
const form = reactive<FoodFormState>(emptyFoodForm())
const formLoading = ref(false)
const formLoadError = ref('')
const formError = ref('')
const submitting = ref(false)
const fieldErrors = reactive<Record<string, string>>({})

/** 图片地址随输入实时变化，为空时也显示占位图，避免出现破图 */
const previewImage = computed(() => resolveFoodImage(form.imageUrl.trim()))

function resetFormState() {
  formLoading.value = false
  formLoadError.value = ''
  formError.value = ''
  for (const key of Object.keys(fieldErrors)) delete fieldErrors[key]
}

function openCreate() {
  resetFormState()
  editingId.value = null
  Object.assign(form, emptyFoodForm())
  modalOpen.value = true
}

async function openEdit(item: AdminFoodListItem) {
  resetFormState()
  Object.assign(form, emptyFoodForm())
  editingId.value = item.id
  modalOpen.value = true
  formLoading.value = true

  try {
    // 列表接口不带来源备注等编辑字段，必须回查详情，否则保存会把未展示的字段清空
    const detail = await fetchAdminFood(item.id)
    Object.assign(form, {
      name: detail.name,
      nameEn: detail.nameEn ?? '',
      categoryId: String(detail.categoryId),
      imageUrl: detail.imageUrl ?? '',
      description: detail.description ?? '',
      state: detail.state ?? '',
      fdcId: detail.fdcId === null ? '' : String(detail.fdcId),
      verified: detail.verified,
      sourceNote: detail.sourceNote ?? '',
      claimNote: detail.claimNote ?? '',
    })
  } catch (err) {
    formLoadError.value = err instanceof Error ? err.message : '食物详情加载失败'
  } finally {
    formLoading.value = false
  }
}

function closeModal() {
  if (submitting.value) return
  modalOpen.value = false
}

function validate(): boolean {
  for (const key of Object.keys(fieldErrors)) delete fieldErrors[key]

  const name = form.name.trim()
  if (!name) fieldErrors.name = '请填写食物名称'
  else if (name.length > 64) fieldErrors.name = '名称不能超过 64 个字符'

  if (!form.categoryId) fieldErrors.categoryId = '请选择分类'

  const imageUrl = form.imageUrl.trim()
  if (!imageUrl) fieldErrors.imageUrl = '请填写图片地址'
  else if (!imageUrl.startsWith('/')) fieldErrors.imageUrl = '图片地址必须以 / 开头'

  if (form.description.length > 255) fieldErrors.description = '介绍不能超过 255 个字符'

  const fdcId = form.fdcId.trim()
  if (fdcId && !/^\d+$/.test(fdcId)) fieldErrors.fdcId = 'FDC ID 只能填写数字'

  return Object.keys(fieldErrors).length === 0
}

/** 空字符串统一转成 null，与后端「可空字段」的约定保持一致 */
function optionalText(value: string): string | null {
  const text = value.trim()
  return text ? text : null
}

function buildPayload(): AdminFoodForm {
  return {
    name: form.name.trim(),
    nameEn: optionalText(form.nameEn),
    categoryId: Number(form.categoryId),
    imageUrl: form.imageUrl.trim(),
    description: optionalText(form.description),
    state: optionalText(form.state),
    fdcId: form.fdcId.trim() ? Number(form.fdcId.trim()) : null,
    verified: form.verified,
    sourceNote: optionalText(form.sourceNote),
    claimNote: optionalText(form.claimNote),
  }
}

async function submitForm() {
  if (submitting.value || formLoading.value || formLoadError.value) return
  formError.value = ''
  if (!validate()) return

  submitting.value = true
  try {
    const payload = buildPayload()
    if (editingId.value === null) await createFood(payload)
    else await updateFood(editingId.value, payload)

    modalOpen.value = false
    await loadFoods()
  } catch (err) {
    // 后端 message 比通用文案具体（例如「名称已存在」），优先原样展示
    formError.value = err instanceof Error ? err.message : '保存失败，请稍后重试'
  } finally {
    submitting.value = false
  }
}

/* ---------- 删除 ---------- */

const removingId = ref<number | null>(null)

async function removeFood(item: AdminFoodListItem) {
  // 删除不可恢复，用浏览器确认框加一道拦截，避免误点操作列
  if (!window.confirm(`确定删除「${item.name}」吗？删除后无法恢复。`)) return

  actionError.value = ''
  removingId.value = item.id
  try {
    await deleteFood(item.id)
    // 删除当前页最后一条时回退一页，否则会停留在空页
    if (items.value.length === 1 && page.value > 1) page.value -= 1
    await loadFoods()
  } catch (err) {
    actionError.value = err instanceof Error ? err.message : '删除失败，请稍后重试'
  } finally {
    removingId.value = null
  }
}

onMounted(() => {
  loadCategories()
  loadFoods()
})
</script>

<template>
  <section class="admin-panel">
    <div class="admin-toolbar">
      <form class="admin-search" role="search" @submit.prevent="submitSearch">
        <Search aria-hidden="true" />
        <input
          v-model="keywordInput"
          type="search"
          placeholder="搜索食物名称"
          aria-label="搜索食物名称"
        />
      </form>
      <button type="button" class="admin-button" @click="submitSearch">搜索</button>

      <select v-model="categoryCode" class="admin-select" aria-label="按分类筛选" @change="changeCategory">
        <option value="">全部分类</option>
        <option v-for="category in categories" :key="category.id" :value="category.code">
          {{ category.name }}
        </option>
      </select>

      <button type="button" class="admin-button admin-button--primary admin-toolbar__spacer" @click="openCreate">
        <Plus aria-hidden="true" />
        <span>新增食物</span>
      </button>
    </div>

    <p v-if="categoriesError" class="admin-alert admin-alert--error admin-alert--panel">
      分类列表加载失败：{{ categoriesError }}
    </p>

    <p v-if="actionError" class="admin-alert admin-alert--error admin-alert--panel">{{ actionError }}</p>

    <div v-if="loading" class="admin-state">
      <LoaderCircle class="admin-spin" aria-hidden="true" />
      <h3>正在加载食物列表</h3>
      <p>请稍候……</p>
    </div>

    <div v-else-if="error" class="admin-state">
      <TriangleAlert aria-hidden="true" />
      <h3>加载失败</h3>
      <p>{{ error }}</p>
      <button type="button" class="admin-button" @click="loadFoods">重新加载</button>
    </div>

    <div v-else-if="!items.length" class="admin-state">
      <SearchX aria-hidden="true" />
      <h3>暂无食物数据</h3>
      <p v-if="appliedKeyword || categoryCode">当前筛选条件下没有结果，试试其它关键词或分类</p>
      <p v-else>还没有任何食物记录，先新增一条吧</p>
      <button
        v-if="appliedKeyword || categoryCode"
        type="button"
        class="admin-button"
        @click="clearFilters"
      >
        清空筛选
      </button>
      <button v-else type="button" class="admin-button admin-button--primary" @click="openCreate">
        <Plus aria-hidden="true" />
        <span>新增食物</span>
      </button>
    </div>

    <template v-else>
      <div class="admin-table-wrap">
        <table class="admin-table">
          <caption class="admin-sr-only">食物管理列表</caption>
          <thead>
            <tr>
              <th scope="col">缩略图</th>
              <th scope="col">ID</th>
              <th scope="col">名称</th>
              <th scope="col">分类</th>
              <th scope="col">状态</th>
              <th scope="col">更新时间</th>
              <th scope="col">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in items" :key="item.id">
              <td>
                <!-- 名称就在旁边，缩略图按装饰图处理，空 alt 避免读屏重复 -->
                <img
                  class="admin-thumb"
                  :src="resolveFoodImage(item.imageUrl)"
                  alt=""
                  @error="handleFoodImageError"
                />
              </td>
              <td class="admin-table__id">{{ item.id }}</td>
              <td>
                <div class="admin-table__name">{{ item.name }}</div>
                <div v-if="item.nameEn" class="admin-table__sub">{{ item.nameEn }}</div>
              </td>
              <td>
                <span class="category-tag" :class="categoryTone(item.categoryCode)">{{ item.categoryName }}</span>
              </td>
              <td>
                <span class="admin-badge" :class="item.verified ? 'admin-badge--ok' : 'admin-badge--idle'">
                  {{ item.verified ? '已核验' : '待核验' }}
                </span>
              </td>
              <td class="admin-table__time">{{ formatTime(item.updatedAt) }}</td>
              <td>
                <div class="admin-table__actions">
                  <button type="button" class="admin-button admin-button--sm" @click="openEdit(item)">
                    <Pencil aria-hidden="true" />
                    <span>编辑</span>
                  </button>
                  <button
                    type="button"
                    class="admin-button admin-button--sm admin-button--danger"
                    :disabled="removingId === item.id"
                    @click="removeFood(item)"
                  >
                    <Trash2 aria-hidden="true" />
                    <span>{{ removingId === item.id ? '删除中…' : '删除' }}</span>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
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

  <div v-if="modalOpen" class="admin-modal" @click.self="closeModal">
    <div class="admin-modal__dialog" role="dialog" aria-modal="true" aria-labelledby="food-form-title">
      <div class="admin-modal__head">
        <h2 id="food-form-title" class="admin-modal__title">
          {{ editingId === null ? '新增食物' : '编辑食物' }}
        </h2>
        <button type="button" class="admin-modal__close" aria-label="关闭弹窗" @click="closeModal">
          <X aria-hidden="true" />
        </button>
      </div>

      <div v-if="formLoading" class="admin-state admin-state--compact">
        <LoaderCircle class="admin-spin" aria-hidden="true" />
        <p>正在加载食物信息……</p>
      </div>

      <div v-else-if="formLoadError" class="admin-modal__body">
        <p class="admin-alert admin-alert--error admin-alert--inline">{{ formLoadError }}</p>
        <p class="admin-field__hint">未取到完整数据时不提交，避免误把来源备注等字段清空。</p>
        <div class="admin-modal__foot">
          <button type="button" class="admin-button" @click="closeModal">关闭</button>
        </div>
      </div>

      <form v-else @submit.prevent="submitForm">
        <div class="admin-modal__body">
          <p v-if="formError" class="admin-alert admin-alert--error admin-alert--inline">{{ formError }}</p>

          <div class="admin-form-grid">
            <label class="admin-field">
              <span class="admin-field__label">名称 <span aria-hidden="true">*</span></span>
              <input
                v-model="form.name"
                class="admin-input"
                :class="{ 'is-invalid': Boolean(fieldErrors.name) }"
                type="text"
                maxlength="64"
                :aria-invalid="Boolean(fieldErrors.name)"
              />
              <span v-if="fieldErrors.name" class="admin-field__error">{{ fieldErrors.name }}</span>
            </label>

            <label class="admin-field">
              <span class="admin-field__label">英文名</span>
              <input v-model="form.nameEn" class="admin-input" type="text" maxlength="120" />
            </label>

            <label class="admin-field">
              <span class="admin-field__label">分类 <span aria-hidden="true">*</span></span>
              <select
                v-model="form.categoryId"
                class="admin-select"
                :class="{ 'is-invalid': Boolean(fieldErrors.categoryId) }"
                :aria-invalid="Boolean(fieldErrors.categoryId)"
              >
                <option value="" disabled>请选择分类</option>
                <option v-for="category in categories" :key="category.id" :value="String(category.id)">
                  {{ category.name }}
                </option>
              </select>
              <span v-if="fieldErrors.categoryId" class="admin-field__error">{{ fieldErrors.categoryId }}</span>
            </label>

            <div class="admin-field">
              <label class="admin-field__label" for="food-image-url">图片地址 <span aria-hidden="true">*</span></label>
              <div class="admin-field__row">
                <input
                  id="food-image-url"
                  v-model="form.imageUrl"
                  class="admin-input"
                  :class="{ 'is-invalid': Boolean(fieldErrors.imageUrl) }"
                  type="text"
                  placeholder="/foods/74-xxx.webp"
                  :aria-invalid="Boolean(fieldErrors.imageUrl)"
                />
                <img
                  class="admin-field__preview"
                  :src="previewImage"
                  alt="图片预览"
                  @error="handleFoodImageError"
                />
              </div>
              <span v-if="fieldErrors.imageUrl" class="admin-field__error">{{ fieldErrors.imageUrl }}</span>
              <span v-else class="admin-field__hint">站内相对路径，以 / 开头</span>
            </div>

            <label class="admin-field">
              <span class="admin-field__label">状态说明</span>
              <input
                v-model="form.state"
                class="admin-input"
                type="text"
                maxlength="60"
                placeholder="如：生、带皮"
              />
            </label>

            <label class="admin-field">
              <span class="admin-field__label">FDC ID</span>
              <input
                v-model="form.fdcId"
                class="admin-input"
                :class="{ 'is-invalid': Boolean(fieldErrors.fdcId) }"
                type="text"
                inputmode="numeric"
                :aria-invalid="Boolean(fieldErrors.fdcId)"
              />
              <span v-if="fieldErrors.fdcId" class="admin-field__error">{{ fieldErrors.fdcId }}</span>
            </label>

            <div class="admin-field admin-field--full">
              <span class="admin-field__label">核验状态</span>
              <label class="admin-checkbox">
                <input v-model="form.verified" type="checkbox" />
                <span>数值已对照官方来源核验</span>
              </label>
            </div>

            <label class="admin-field admin-field--full">
              <span class="admin-field__label">介绍</span>
              <textarea
                v-model="form.description"
                class="admin-textarea"
                :class="{ 'is-invalid': Boolean(fieldErrors.description) }"
                maxlength="255"
                :aria-invalid="Boolean(fieldErrors.description)"
              ></textarea>
              <span v-if="fieldErrors.description" class="admin-field__error">{{ fieldErrors.description }}</span>
              <span v-else class="admin-field__hint">{{ form.description.length }} / 255</span>
            </label>

            <label class="admin-field">
              <span class="admin-field__label">来源备注</span>
              <textarea v-model="form.sourceNote" class="admin-textarea" maxlength="300"></textarea>
            </label>

            <label class="admin-field">
              <span class="admin-field__label">营养声称备注</span>
              <textarea v-model="form.claimNote" class="admin-textarea" maxlength="300"></textarea>
            </label>
          </div>
        </div>

        <div class="admin-modal__foot">
          <button type="button" class="admin-button" :disabled="submitting" @click="closeModal">取消</button>
          <button type="submit" class="admin-button admin-button--primary" :disabled="submitting">
            {{ submitting ? '保存中…' : '保存' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>