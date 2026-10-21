<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { LoaderCircle, Pencil, Plus, Tags, Trash2, TriangleAlert, X } from 'lucide-vue-next'
import {
  createCategory,
  deleteCategory,
  fetchAdminCategories,
  updateCategory,
} from '@/services/admin'
import type { AdminCategory, AdminCategoryForm } from '@/types/admin'

const categories = ref<AdminCategory[]>([])
const loading = ref(false)
const error = ref('')
/** 删除失败不影响表格展示，单独提示，避免整页被错误态替换 */
const actionError = ref('')

async function loadCategories() {
  loading.value = true
  error.value = ''

  try {
    categories.value = await fetchAdminCategories()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '分类列表加载失败'
  } finally {
    loading.value = false
  }
}

/* ---------- 新增 / 编辑弹窗 ---------- */

interface CategoryFormState {
  code: string
  name: string
  sortOrder: string
}

function emptyCategoryForm(): CategoryFormState {
  return { code: '', name: '', sortOrder: '0' }
}

const modalOpen = ref(false)
const editingId = ref<number | null>(null)
const form = reactive<CategoryFormState>(emptyCategoryForm())
const fieldErrors = reactive<Record<string, string>>({})
const formError = ref('')
const submitting = ref(false)

function resetFormState() {
  formError.value = ''
  for (const key of Object.keys(fieldErrors)) delete fieldErrors[key]
}

function openCreate() {
  resetFormState()
  editingId.value = null
  Object.assign(form, emptyCategoryForm())
  modalOpen.value = true
}

function openEdit(category: AdminCategory) {
  resetFormState()
  editingId.value = category.id
  Object.assign(form, {
    code: category.code,
    name: category.name,
    sortOrder: String(category.sortOrder),
  })
  modalOpen.value = true
}

function closeModal() {
  if (submitting.value) return
  modalOpen.value = false
}

function validate(): boolean {
  for (const key of Object.keys(fieldErrors)) delete fieldErrors[key]

  const code = form.code.trim()
  if (!code) fieldErrors.code = '请填写分类编码'
  else if (!/^[A-Z0-9_]+$/.test(code)) fieldErrors.code = '编码只能使用大写字母、数字和下划线'

  if (!form.name.trim()) fieldErrors.name = '请填写分类名称'

  const sortOrder = form.sortOrder.trim()
  if (sortOrder && !/^-?\d+$/.test(sortOrder)) fieldErrors.sortOrder = '排序必须是整数'

  return Object.keys(fieldErrors).length === 0
}

async function submitForm() {
  if (submitting.value) return
  formError.value = ''
  if (!validate()) return

  const payload: AdminCategoryForm = {
    code: form.code.trim(),
    name: form.name.trim(),
    sortOrder: form.sortOrder.trim() ? Number(form.sortOrder.trim()) : 0,
  }

  submitting.value = true
  try {
    if (editingId.value === null) await createCategory(payload)
    else await updateCategory(editingId.value, payload)

    modalOpen.value = false
    await loadCategories()
  } catch (err) {
    // 编码冲突等业务错误由后端给出具体 message，原样展示
    formError.value = err instanceof Error ? err.message : '保存失败，请稍后重试'
  } finally {
    submitting.value = false
  }
}

/* ---------- 删除 ---------- */

const removingId = ref<number | null>(null)

async function removeCategory(category: AdminCategory) {
  // 分类被食物引用时后端返回 409，确认框先把「不可恢复」讲清楚
  if (!window.confirm(`确定删除分类「${category.name}」吗？删除后无法恢复。`)) return

  actionError.value = ''
  removingId.value = category.id
  try {
    await deleteCategory(category.id)
    await loadCategories()
  } catch (err) {
    // 409 的 message 会说明「该分类下仍有 N 个食物」，直接原样提示即可
    actionError.value = err instanceof Error ? err.message : '删除失败，请稍后重试'
  } finally {
    removingId.value = null
  }
}

onMounted(loadCategories)
</script>

<template>
  <section class="admin-panel">
    <div class="admin-toolbar">
      <span class="admin-meta">共 {{ categories.length }} 个分类</span>
      <button type="button" class="admin-button admin-button--primary admin-toolbar__spacer" @click="openCreate">
        <Plus aria-hidden="true" />
        <span>新增分类</span>
      </button>
    </div>

    <p v-if="actionError" class="admin-alert admin-alert--error admin-alert--panel">{{ actionError }}</p>

    <div v-if="loading" class="admin-state">
      <LoaderCircle class="admin-spin" aria-hidden="true" />
      <h3>正在加载分类</h3>
      <p>请稍候……</p>
    </div>

    <div v-else-if="error" class="admin-state">
      <TriangleAlert aria-hidden="true" />
      <h3>加载失败</h3>
      <p>{{ error }}</p>
      <button type="button" class="admin-button" @click="loadCategories">重新加载</button>
    </div>

    <div v-else-if="!categories.length" class="admin-state">
      <Tags aria-hidden="true" />
      <h3>还没有分类</h3>
      <p>食物必须归属到一个分类，先新建一个吧</p>
      <button type="button" class="admin-button admin-button--primary" @click="openCreate">
        <Plus aria-hidden="true" />
        <span>新增分类</span>
      </button>
    </div>

    <div v-else class="admin-table-wrap">
      <table class="admin-table">
        <caption class="admin-sr-only">分类管理列表</caption>
        <thead>
          <tr>
            <th scope="col">ID</th>
            <th scope="col">编码</th>
            <th scope="col">名称</th>
            <th scope="col">排序</th>
            <th scope="col">食物数</th>
            <th scope="col">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="category in categories" :key="category.id">
            <td class="admin-table__id">{{ category.id }}</td>
            <td><code class="admin-code">{{ category.code }}</code></td>
            <td class="admin-table__name">{{ category.name }}</td>
            <td class="admin-table__id">{{ category.sortOrder }}</td>
            <td class="admin-table__id">{{ category.foodCount }}</td>
            <td>
              <div class="admin-table__actions">
                <button type="button" class="admin-button admin-button--sm" @click="openEdit(category)">
                  <Pencil aria-hidden="true" />
                  <span>编辑</span>
                </button>
                <button
                  type="button"
                  class="admin-button admin-button--sm admin-button--danger"
                  :disabled="removingId === category.id"
                  @click="removeCategory(category)"
                >
                  <Trash2 aria-hidden="true" />
                  <span>{{ removingId === category.id ? '删除中…' : '删除' }}</span>
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>

  <div v-if="modalOpen" class="admin-modal" @click.self="closeModal">
    <div class="admin-modal__dialog admin-modal__dialog--narrow" role="dialog" aria-modal="true" aria-labelledby="category-form-title">
      <div class="admin-modal__head">
        <h2 id="category-form-title" class="admin-modal__title">
          {{ editingId === null ? '新增分类' : '编辑分类' }}
        </h2>
        <button type="button" class="admin-modal__close" aria-label="关闭弹窗" @click="closeModal">
          <X aria-hidden="true" />
        </button>
      </div>

      <form @submit.prevent="submitForm">
        <div class="admin-modal__body">
          <p v-if="formError" class="admin-alert admin-alert--error admin-alert--inline">{{ formError }}</p>

          <div class="admin-form-grid">
            <label class="admin-field">
              <span class="admin-field__label">编码 <span aria-hidden="true">*</span></span>
              <input
                v-model="form.code"
                class="admin-input"
                :class="{ 'is-invalid': Boolean(fieldErrors.code) }"
                type="text"
                placeholder="VEGETABLE"
                :aria-invalid="Boolean(fieldErrors.code)"
              />
              <span v-if="fieldErrors.code" class="admin-field__error">{{ fieldErrors.code }}</span>
              <span v-else class="admin-field__hint">大写字母 / 数字 / 下划线</span>
            </label>

            <label class="admin-field">
              <span class="admin-field__label">名称 <span aria-hidden="true">*</span></span>
              <input
                v-model="form.name"
                class="admin-input"
                :class="{ 'is-invalid': Boolean(fieldErrors.name) }"
                type="text"
                maxlength="32"
                placeholder="蔬菜"
                :aria-invalid="Boolean(fieldErrors.name)"
              />
              <span v-if="fieldErrors.name" class="admin-field__error">{{ fieldErrors.name }}</span>
            </label>

            <label class="admin-field admin-field--full">
              <span class="admin-field__label">排序</span>
              <input
                v-model="form.sortOrder"
                class="admin-input"
                :class="{ 'is-invalid': Boolean(fieldErrors.sortOrder) }"
                type="number"
                step="1"
                :aria-invalid="Boolean(fieldErrors.sortOrder)"
              />
              <span v-if="fieldErrors.sortOrder" class="admin-field__error">{{ fieldErrors.sortOrder }}</span>
              <span v-else class="admin-field__hint">数值小的排在前面</span>
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