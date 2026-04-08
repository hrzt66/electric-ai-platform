<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { usePlatformStore } from '../stores/platform'

const router = useRouter()
const platformStore = usePlatformStore()
const modelPageLoading = ref(false)
const modelPageError = ref('')

const generationModels = computed(() => platformStore.models.filter((item) => item.model_type === 'generation'))
const scoringModels = computed(() => platformStore.models.filter((item) => item.model_type === 'scoring'))

function jumpToGenerate(modelName: string) {
  router.push({ path: '/generate', query: { model: modelName } })
}

const hasModelData = computed(() => platformStore.models.length > 0)

async function loadModelPage() {
  modelPageLoading.value = !hasModelData.value
  modelPageError.value = ''

  try {
    await platformStore.fetchModels()
  } catch (error) {
    modelPageError.value = platformStore.modelsLoadError || '模型中心加载失败，请检查模型服务与网关链路。'
  } finally {
    modelPageLoading.value = false
  }
}

onMounted(() => {
  void loadModelPage()
})
</script>

<template>
  <div class="model-page">
    <el-alert v-if="modelPageError" :closable="false" type="warning" show-icon :title="modelPageError" />

    <el-skeleton v-if="modelPageLoading" class="page-skeleton" animated :rows="10" />

    <template v-else>
      <section class="hero">
        <div>
          <p class="hero-eyebrow">模型目录</p>
          <h2 class="hero-title">模型中心</h2>
        </div>
        <el-tag type="info">状态来自 Go 目录探测与 Python 运行时检查</el-tag>
      </section>

      <section class="model-section">
        <div class="section-header">
          <h3>生成模型</h3>
          <span>{{ generationModels.length }} 个</span>
        </div>
        <div class="model-grid">
          <article v-for="model in generationModels" :key="model.id" class="model-card">
            <div class="card-top">
              <div>
                <p class="model-type">{{ model.model_type }}</p>
                <h3>{{ model.display_name || model.model_name }}</h3>
              </div>
              <el-tag :type="model.status === 'available' ? 'success' : model.status === 'experimental' ? 'warning' : 'info'">
                {{ model.status }}
              </el-tag>
            </div>
            <p class="description">{{ model.description || '暂无模型说明' }}</p>
            <dl class="meta">
              <div>
                <dt>服务</dt>
                <dd>{{ model.service_name }}</dd>
              </div>
              <div>
                <dt>本地路径</dt>
                <dd>{{ model.local_path || '未配置' }}</dd>
              </div>
              <div>
                <dt>默认 Prompt</dt>
                <dd>{{ model.default_positive_prompt || '无' }}</dd>
              </div>
            </dl>
            <el-button type="primary" plain @click="jumpToGenerate(model.model_name)">在工作台使用</el-button>
          </article>
        </div>
      </section>

      <section class="model-section">
        <div class="section-header">
          <h3>评分模型</h3>
          <span>{{ scoringModels.length }} 个</span>
        </div>
        <div class="model-grid">
          <article v-for="model in scoringModels" :key="model.id" class="model-card">
            <div class="card-top">
              <div>
                <p class="model-type">{{ model.model_type }}</p>
                <h3>{{ model.display_name || model.model_name }}</h3>
              </div>
              <el-tag :type="model.status === 'available' ? 'success' : model.status === 'experimental' ? 'warning' : 'info'">
                {{ model.status }}
              </el-tag>
            </div>
            <p class="description">{{ model.description || '暂无模型说明' }}</p>
            <dl class="meta">
              <div>
                <dt>服务</dt>
                <dd>{{ model.service_name }}</dd>
              </div>
              <div>
                <dt>本地路径</dt>
                <dd>{{ model.local_path || '未配置' }}</dd>
              </div>
            </dl>
          </article>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.model-page {
  display: grid;
  gap: 20px;
}

.page-skeleton {
  border-radius: 24px;
  padding: 24px;
  background: #ffffff;
  box-shadow: var(--ea-shadow);
}

.hero,
.model-card {
  border-radius: 24px;
  background: #ffffff;
  box-shadow: var(--ea-shadow);
}

.hero {
  padding: 22px;
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
}

.hero-eyebrow,
.hero-title,
.model-type,
.description,
.meta dt,
.meta dd,
.model-card h3,
.section-header h3,
.section-header span {
  margin: 0;
}

.hero-eyebrow,
.model-type {
  color: #8a5c18;
  font-size: 0.82rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.hero-title {
  margin-top: 6px;
  color: #17202b;
  font-size: 1.6rem;
}

.model-section {
  display: grid;
  gap: 14px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: #17202b;
}

.model-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
}

.model-card {
  padding: 22px;
  display: grid;
  gap: 14px;
}

.card-top {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  align-items: flex-start;
}

.model-card h3 {
  margin-top: 6px;
  color: #17202b;
}

.description {
  color: #53606f;
  line-height: 1.6;
}

.meta {
  display: grid;
  gap: 12px;
}

.meta div {
  display: grid;
  gap: 4px;
  padding: 12px 14px;
  border-radius: 16px;
  background: #f8fafc;
}

.meta dt {
  color: #64748b;
  font-size: 0.82rem;
}

.meta dd {
  color: #17202b;
  word-break: break-all;
}

@media (max-width: 920px) {
  .model-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .hero,
  .section-header,
  .card-top {
    flex-direction: column;
    align-items: stretch;
  }

  .model-card {
    padding: 18px;
  }
}
</style>
