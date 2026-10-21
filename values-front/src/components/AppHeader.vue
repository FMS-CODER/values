<script setup lang="ts">
import { ref } from 'vue'
import { storeToRefs } from 'pinia'
import { Search, Sun, UserRound, X } from 'lucide-vue-next'
import { useFoodStore } from '@/stores/food'

const store = useFoodStore()
const { searchKeyword } = storeToRefs(store)
const searchInput = ref<HTMLInputElement | null>(null)

function clearSearch() {
  store.setSearchKeyword('')
  // 清空后保留输入焦点，方便用户直接输入下一个关键词
  searchInput.value?.focus()
}
</script>

<template>
  <header class="app-header">
    <div class="search-box">
      <Search class="search-box__icon" aria-hidden="true" />
      <input
        ref="searchInput"
        v-model="searchKeyword"
        type="search"
        aria-label="搜索食物"
        placeholder="搜索食物名称，如：西兰花、苹果、鸡蛋……"
      />
      <button
        v-if="searchKeyword"
        type="button"
        class="search-box__clear"
        aria-label="清空搜索"
        @click="clearSearch"
      >
        <X aria-hidden="true" />
      </button>
    </div>

    <div class="header-actions">
      <button type="button" class="icon-button" aria-label="主题切换（暂未开放）" title="主题切换（暂未开放）">
        <Sun aria-hidden="true" />
      </button>
      <div class="avatar" role="img" aria-label="用户头像占位">
        <UserRound aria-hidden="true" />
      </div>
    </div>
  </header>
</template>
