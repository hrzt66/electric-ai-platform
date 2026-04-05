<script setup lang="ts">
import { computed } from 'vue'

import type { GenerateTaskRequest, ModelRecord } from '../../types/platform'

const props = defineProps<{
  form: GenerateTaskRequest
  models: ModelRecord[]
  submitting: boolean
}>()

const emit = defineEmits<{
  submit: []
  fillDefaults: [model: ModelRecord]
}>()

// 当前选中模型的说明会在面板顶部展示，帮助用户理解不同模型的定位。
const selectedModel = computed(() => props.models.find((item) => item.model_name === props.form.model_name) ?? null)
</script>

<template>
  <section class="panel">
    <div class="panel-header">
      <div>
        <p class="panel-eyebrow">生成输入</p>
        <h2 class="panel-title">参数工作台</h2>
      </div>
      <el-tag type="warning" effect="dark">真实生成</el-tag>
    </div>

    <el-form label-position="top" class="form" size="small">
      <el-form-item label="生成模型">
        <el-select v-model="form.model_name" size="small" style="width: 100%">
          <el-option
            v-for="item in models"
            :key="item.model_name"
            :label="item.display_name || item.model_name"
            :value="item.model_name"
          />
        </el-select>
      </el-form-item>

      <div v-if="selectedModel" class="model-tip">
        <p class="tip-name">{{ selectedModel.display_name || selectedModel.model_name }}</p>
        <p class="tip-text">{{ selectedModel.description || '暂无模型说明' }}</p>
        <el-button size="small" text type="primary" @click="emit('fillDefaults', selectedModel)">应用推荐提示词</el-button>
      </div>

      <el-form-item label="正向提示词">
        <el-input v-model="form.prompt" type="textarea" :rows="4" size="small" placeholder="描述你想生成的工业电力场景。" />
      </el-form-item>

      <el-form-item label="负向提示词">
        <el-input v-model="form.negative_prompt" type="textarea" :rows="2" size="small" placeholder="描述你想避免的瑕疵、失真或风格。" />
      </el-form-item>

      <div class="grid-two">
        <el-form-item label="随机种子">
          <el-input-number v-model="form.seed" size="small" :min="-1" :max="2147483647" controls-position="right" />
        </el-form-item>

        <el-form-item label="采样步数">
          <el-input-number v-model="form.steps" size="small" :min="1" :max="80" controls-position="right" />
        </el-form-item>

        <el-form-item label="引导强度">
          <el-input-number v-model="form.guidance_scale" size="small" :min="1" :max="20" :step="0.5" controls-position="right" />
        </el-form-item>

        <el-form-item label="输出数量">
          <el-input-number v-model="form.num_images" size="small" :min="1" :max="4" controls-position="right" />
        </el-form-item>
      </div>

      <div class="grid-two">
        <el-form-item label="宽度">
          <el-slider v-model="form.width" :min="64" :max="1024" :step="64" show-input />
        </el-form-item>

        <el-form-item label="高度">
          <el-slider v-model="form.height" :min="64" :max="1024" :step="64" show-input />
        </el-form-item>
      </div>

      <el-button type="primary" class="submit-button" :loading="submitting" @click="emit('submit')">
        {{ submitting ? '正在提交任务...' : '提交真实生成任务' }}
      </el-button>
    </el-form>
  </section>
</template>

<style scoped>
.panel {
  height: 100%;
  min-height: 0;
  padding: 16px;
  border-radius: 22px;
  background: #ffffff;
  box-shadow: var(--ea-shadow);
  display: flex;
  flex-direction: column;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 10px;
  margin-bottom: 12px;
}

.panel-eyebrow,
.panel-title,
.tip-name,
.tip-text {
  margin: 0;
}

.panel-eyebrow {
  font-size: 0.76rem;
  color: #8a5c18;
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.panel-title {
  margin-top: 4px;
  font-size: 1.28rem;
  color: #17202b;
}

.model-tip {
  margin-bottom: 10px;
  padding: 10px 12px;
  border-radius: 14px;
  background: linear-gradient(135deg, rgba(211, 164, 73, 0.12), rgba(19, 81, 180, 0.06));
}

.tip-name {
  font-weight: 600;
  color: #17202b;
  font-size: 0.95rem;
}

.tip-text {
  margin-top: 4px;
  color: #53606f;
  font-size: 0.84rem;
  line-height: 1.4;
}

.form {
  flex: 1;
  min-height: 0;
  overflow: auto;
  display: grid;
  gap: 2px;
  padding-right: 4px;
}

.grid-two {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.submit-button {
  width: 100%;
  min-height: 40px;
  margin-top: 4px;
  border-radius: 12px;
  background: linear-gradient(90deg, #1347a8, #0f6ac4);
  border: 0;
}

:deep(.el-form-item) {
  margin-bottom: 8px;
}

:deep(.el-form-item__label) {
  padding-bottom: 4px;
  line-height: 1.25;
}

:deep(.el-input-number) {
  width: 100%;
}

:deep(.el-slider__runway) {
  margin: 10px 0;
}

:deep(.el-slider__input) {
  width: 84px;
}

:deep(.el-textarea__inner) {
  line-height: 1.45;
}

@media (max-width: 700px) {
  .grid-two {
    grid-template-columns: 1fr;
  }
}
</style>
