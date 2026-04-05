<script setup lang="ts">
import { reactive } from 'vue'
import { useRouter } from 'vue-router'

import { http } from '../api/http'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const form = reactive({ username: 'admin', password: 'admin123456' })

async function submit() {
  const { data } = await http.post('/auth/login', form)
  authStore.setSession({
    accessToken: data.data.access_token,
    userName: data.data.user_name,
    displayName: data.data.display_name,
  })
  router.push('/generate')
}
</script>

<template>
  <div class="page">
    <el-card class="login-card">
      <template #header>
        <span>Electric AI Login</span>
      </template>
      <el-form @submit.prevent="submit">
        <el-form-item label="账号"><el-input v-model="form.username" /></el-form-item>
        <el-form-item label="密码"><el-input v-model="form.password" type="password" /></el-form-item>
        <el-button type="primary" @click="submit">登录</el-button>
      </el-form>
    </el-card>
  </div>
</template>

<style scoped>
.page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  background: linear-gradient(135deg, #eef4ff, #f8fbff);
}

.login-card {
  width: min(420px, calc(100vw - 32px));
}
</style>
