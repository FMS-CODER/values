<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import { Apple, House, Leaf } from 'lucide-vue-next'

const route = useRoute()

const isHome = computed(() => route.path === '/')
const isFoods = computed(() => route.path.startsWith('/foods'))
</script>

<template>
  <aside class="sidebar">
    <RouterLink to="/" class="brand" aria-label="返回首页">
      <span class="brand__mark">
        <Leaf aria-hidden="true" />
      </span>
      <span class="brand__text">
        <span class="brand__name">食物营养百科</span>
        <span class="brand__tagline">发现食物的营养价值</span>
      </span>
    </RouterLink>

    <nav class="sidebar__nav" aria-label="主导航">
      <RouterLink to="/" class="nav-item" :class="{ 'is-active': isHome }" :aria-current="isHome ? 'page' : undefined">
        <House aria-hidden="true" />
        <span>首页</span>
      </RouterLink>
      <RouterLink
        to="/foods"
        class="nav-item"
        :class="{ 'is-active': isFoods }"
        :aria-current="isFoods ? 'page' : undefined"
      >
        <Apple aria-hidden="true" />
        <span>食物</span>
      </RouterLink>
    </nav>

    <p class="sidebar__footer">营养数据为界面演示用示例值，不作为膳食或医学建议。</p>
  </aside>
</template>
