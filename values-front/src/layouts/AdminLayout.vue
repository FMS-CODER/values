<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'
import { ArrowLeft, Images, Leaf, Salad, Tags } from 'lucide-vue-next'

const route = useRoute()

/**
 * 顶部标题取自路由 meta。
 * 管理端三个页面共用一个横条，标题跟着路由走比每个页面各画一个标题更省重复代码。
 */
const pageTitle = computed(() => {
  const title = route.meta.title
  return typeof title === 'string' ? title : '内容管理'
})

const navItems = [
  { to: '/admin/foods', label: '食物管理', icon: Salad },
  { to: '/admin/categories', label: '分类管理', icon: Tags },
  { to: '/admin/images', label: '图片审核', icon: Images },
]
</script>

<template>
  <div class="admin-shell">
    <aside class="admin-sidebar">
      <div class="admin-brand">
        <span class="admin-brand__mark">
          <Leaf aria-hidden="true" />
        </span>
        <span class="admin-brand__text">
          <span class="admin-brand__title">内容管理</span>
          <span class="admin-brand__subtitle">食物营养百科</span>
        </span>
      </div>

      <nav class="admin-nav" aria-label="管理导航">
        <RouterLink
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="admin-nav__item"
          active-class="is-active"
        >
          <component :is="item.icon" aria-hidden="true" />
          <span>{{ item.label }}</span>
        </RouterLink>
      </nav>

      <div class="admin-sidebar__footer">
        <RouterLink to="/" class="admin-sidebar__back">
          <ArrowLeft aria-hidden="true" />
          <span>返回前台</span>
        </RouterLink>
      </div>
    </aside>

    <div class="admin-body">
      <header class="admin-topbar">
        <h1 class="admin-topbar__title">{{ pageTitle }}</h1>
        <div class="admin-topbar__actions">
          <RouterLink to="/" class="admin-button">
            <ArrowLeft aria-hidden="true" />
            <span>返回前台</span>
          </RouterLink>
        </div>
      </header>

      <main class="admin-content">
        <RouterView />
      </main>
    </div>
  </div>
</template>