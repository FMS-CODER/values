<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import { Bot, House, Leaf } from 'lucide-vue-next'

const route = useRoute()

// 食物详情挂在首页浏览路径下，保持「首页」导航高亮
const isHome = computed(() => route.path === '/' || route.path.startsWith('/foods/'))
const isAssistant = computed(() => route.path.startsWith('/assistant'))
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
        to="/assistant"
        class="nav-item"
        :class="{ 'is-active': isAssistant }"
        :aria-current="isAssistant ? 'page' : undefined"
      >
        <Bot aria-hidden="true" />
        <span>AI 助手</span>
      </RouterLink>
    </nav>

    <!-- 侧栏底部落款：一片叶片插画 + 品牌标识，避免底部只剩一行小字显得空荡 -->
    <div class="sidebar__footer">
      <svg class="sidebar__footer-art" viewBox="0 0 96 58" aria-hidden="true">
        <path d="M92 4C64 1 38 12 27 36c21 3 48-11 65-32Z" fill="currentColor" opacity="0.45" />
        <path d="M78 20C59 24 43 37 35 55c19-5 36-19 43-35Z" fill="currentColor" opacity="0.28" />
        <path d="M62 10C46 24 35 40 31 56" stroke="currentColor" stroke-width="1.4" fill="none" opacity="0.6" />
      </svg>

      <!-- 底部 logo 区块：叶片标记 + 品牌名，构成与顶部一致的品牌落款 -->
      <div class="sidebar__footer-brand">
        <span class="sidebar__footer-mark">
          <Leaf aria-hidden="true" />
        </span>
        <span class="sidebar__footer-title">
          食物营养百科
          <span>科学饮食 · 让健康更简单</span>
        </span>
      </div>

      <p class="sidebar__footer-note">营养数据为界面演示用示例值，不作为膳食或医学建议。</p>
    </div>
  </aside>
</template>
