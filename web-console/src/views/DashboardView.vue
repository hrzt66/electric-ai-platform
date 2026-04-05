<script setup lang="ts">
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()
</script>

<template>
  <div class="page">
    <el-card>
      <template #header>
        <span>Dashboard</span>
      </template>
      <p>当前用户：{{ authStore.displayName || authStore.userName || '未登录' }}</p>
      <el-link href="/generate">进入生成页面</el-link>
    </el-card>
  </div>
</template>

<style scoped>
.page {
  padding: 32px;
}
</style>
