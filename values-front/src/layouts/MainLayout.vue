<script setup lang="ts">
import { onMounted } from 'vue'
import { RouterView } from 'vue-router'
import AppSidebar from '@/components/AppSidebar.vue'
import AppHeader from '@/components/AppHeader.vue'
import { useFoodStore } from '@/stores/food'

const store = useFoodStore()

// 布局挂载时一次性拉取分类与列表，供首页和食物百科页共用，避免各页面重复请求
onMounted(() => {
  store.loadCatalog()
})
</script>

<template>
  <div class="app-shell">
    <AppSidebar />

    <div class="app-body">
      <AppHeader />
      <main class="app-main">
        <RouterView />
      </main>
    </div>
  </div>
</template>
