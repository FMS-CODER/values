<script setup lang="ts">
import { RouterView } from 'vue-router'
import AppSidebar from '@/components/AppSidebar.vue'
import AppHeader from '@/components/AppHeader.vue'
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
