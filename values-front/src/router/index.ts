import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '@/views/HomeView.vue'
import MainLayout from '@/layouts/MainLayout.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      component: MainLayout,
      children: [
        {
          path: '',
          name: 'home',
          component: HomeView,
        },
        // 食物页与首页内容重复，统一由首页承载；保留旧地址跳转，避免历史链接失效
        { path: 'foods', redirect: '/' },
        {
          path: 'foods/:id',
          name: 'food-detail',
          component: () => import('@/views/FoodDetailView.vue'),
        },
        {
          path: 'assistant',
          name: 'assistant',
          component: () => import('@/views/AssistantView.vue'),
        },
      ],
    },
    {
      path: '/admin',
      component: () => import('@/layouts/AdminLayout.vue'),
      children: [
        { path: '', redirect: '/admin/foods' },
        {
          path: 'foods',
          name: 'admin-foods',
          component: () => import('@/views/admin/AdminFoodsView.vue'),
          // 顶部横条标题跟着路由走，避免每个管理页各画一个标题
          meta: { title: '食物管理' },
        },
        {
          path: 'categories',
          name: 'admin-categories',
          component: () => import('@/views/admin/AdminCategoriesView.vue'),
          meta: { title: '分类管理' },
        },
        {
          path: 'images',
          name: 'admin-images',
          component: () => import('@/views/admin/AdminImagesView.vue'),
          meta: { title: '图片审核' },
        },
      ],
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/',
    },
  ],
  scrollBehavior() {
    return { top: 0 }
  },
})

export default router