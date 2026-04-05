<script setup lang="ts">
import { reactive, ref } from 'vue'

import { http } from '../api/http'

const form = reactive({
  prompt: 'A wind turbine farm at sunset',
  negative_prompt: 'blurry',
  model_name: 'UniPic-2',
})

const currentJobId = ref<number | null>(null)

async function submit() {
  const { data } = await http.post('/tasks/generate', form)
  currentJobId.value = data.data.id
}
</script>

<template>
  <div class="page">
    <el-card>
      <template #header>
        <span>Create Generate Task</span>
      </template>
      <el-form @submit.prevent="submit">
        <el-form-item label="Prompt"><el-input v-model="form.prompt" type="textarea" /></el-form-item>
        <el-form-item label="Negative Prompt"><el-input v-model="form.negative_prompt" /></el-form-item>
        <el-form-item label="Model"><el-input v-model="form.model_name" /></el-form-item>
        <el-button type="primary" @click="submit">提交生成任务</el-button>
      </el-form>
      <p v-if="currentJobId">当前任务 ID: {{ currentJobId }}</p>
    </el-card>
  </div>
</template>

<style scoped>
.page {
  padding: 32px;
}
</style>
