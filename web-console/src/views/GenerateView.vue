<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useRoute } from 'vue-router'

import AuditTimeline from '../components/audit/AuditTimeline.vue'
import GenerationProgressCard from '../components/workbench/GenerationProgressCard.vue'
import ParameterPanel from '../components/workbench/ParameterPanel.vue'
import ResultPreview from '../components/workbench/ResultPreview.vue'
import ScoreRadar from '../components/workbench/ScoreRadar.vue'
import { usePlatformStore } from '../stores/platform'
import type { GenerateTaskRequest, ModelRecord, ScoreSummary } from '../types/platform'
import { MOBILE_BREAKPOINT, getWorkbenchSections } from '../utils/mobile-layout'
import { FRONTEND_DEFAULT_NEGATIVE_PROMPT, FRONTEND_DEFAULT_POSITIVE_PROMPT } from './generate-defaults'

const FALLBACK_SCORING_MODELS: ModelRecord[] = [
  {
    id: -1,
    model_name: 'electric-score-v1',
    display_name: 'Electric Score V1 (Legacy)',
    model_type: 'scoring',
    service_name: 'python-ai-service',
    status: 'available',
    description: '现有四维评分器，基于 ImageReward、CLIP-IQA 与美学评分运行时。',
    default_positive_prompt: '',
    default_negative_prompt: '',
    local_path: 'G:/electric-ai-runtime/models/scoring/electric-score-v1',
  },
  {
    id: -2,
    model_name: 'electric-score-v2',
    display_name: 'Electric Score V2 (Self-Trained)',
    model_type: 'scoring',
    service_name: 'python-ai-service',
    status: 'available',
    description: '自主训练的轻量四维评分模型，针对电力场景和 6GB 显存环境优化。',
    default_positive_prompt: '',
    default_negative_prompt: '',
    local_path: 'G:/electric-ai-runtime/models/scoring/electric-score-v2',
  },
]

const route = useRoute()
const platformStore = usePlatformStore()
const activeIndex = ref(0)
const pollingInFlight = ref(false)
const workbenchLoading = ref(false)
const workbenchError = ref('')
const viewportWidth = ref(typeof window === 'undefined' ? 1280 : window.innerWidth)
const parameterDrawerOpen = ref(false)
let pollTimer: number | null = null

// 生成表单与后端请求结构保持同名，减少提交时的字段映射成本。
const form = reactive<GenerateTaskRequest>({
  prompt: FRONTEND_DEFAULT_POSITIVE_PROMPT,
  negative_prompt: FRONTEND_DEFAULT_NEGATIVE_PROMPT,
  model_name: 'sd15-electric',
  scoring_model_name: 'electric-score-v1',
  seed: -1,
  steps: 20,
  guidance_scale: 7.5,
  width: 512,
  height: 512,
  num_images: 1,
})

const activeAsset = computed(() => platformStore.currentAssets[activeIndex.value] ?? null)
const generationModels = computed(() => platformStore.models.filter((item) => item.model_type === 'generation'))
const isMobile = computed(() => viewportWidth.value <= MOBILE_BREAKPOINT)
const workbenchSections = computed(() => getWorkbenchSections(viewportWidth.value))
const showInlineControls = computed(() => !isMobile.value && workbenchSections.value[0] === 'controls')
const scoringModels = computed(() => {
  const catalog = platformStore.models.filter(
    (item) => item.model_type === 'scoring' && item.model_name.startsWith('electric-score-'),
  )
  return catalog.length > 0 ? catalog : FALLBACK_SCORING_MODELS
})
const currentModel = computed(() => platformStore.models.find((item) => item.model_name === form.model_name) ?? null)
const activeScores = computed<ScoreSummary | null>(() => {
  if (!activeAsset.value) {
    return null
  }

  return {
    visual_fidelity: activeAsset.value.visual_fidelity,
    text_consistency: activeAsset.value.text_consistency,
    physical_plausibility: activeAsset.value.physical_plausibility,
    composition_aesthetics: activeAsset.value.composition_aesthetics,
    total_score: activeAsset.value.total_score,
  }
})

function stopPolling() {
  if (pollTimer !== null) {
    window.clearInterval(pollTimer)
    pollTimer = null
  }
}

function syncViewport() {
  viewportWidth.value = window.innerWidth
  if (!isMobile.value) {
    parameterDrawerOpen.value = false
  }
}

async function tickTask(taskId: number) {
  // 单个任务轮询期间始终串行刷新，避免前一次请求未结束又发起下一次刷新。
  if (pollingInFlight.value) {
    return
  }

  pollingInFlight.value = true
  try {
    const task = await platformStore.refreshTask(taskId)
    if (task.status === 'completed') {
      ElMessage.success(`任务 #${task.id} 已完成，评分结果已同步。`)
      stopPolling()
    } else if (task.status === 'failed') {
      ElMessage.error(task.error_message || `任务 #${task.id} 执行失败。`)
      stopPolling()
    }
  } catch (error) {
    stopPolling()
    ElMessage.error('刷新任务状态失败，请检查任务服务与网关链路。')
  } finally {
    pollingInFlight.value = false
  }
}

async function startPolling(taskId: number) {
  stopPolling()
  await tickTask(taskId)
  pollTimer = window.setInterval(() => {
    void tickTask(taskId)
  }, 3000)
}

async function submit() {
  try {
    const task = await platformStore.submitGenerateJob({ ...form })
    activeIndex.value = 0
    await startPolling(task.id)
    ElMessage.success(`任务 #${task.id} 已提交，正在进入真实生成链路。`)
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.message || '提交任务失败，请确认已登录并检查网关服务。')
  }
}

function fillDefaults(model: ModelRecord) {
  // 生成模型回退到前端默认提示词，其它模型优先采用注册表里配置的默认词。
  if (model.model_type === 'generation') {
    form.prompt = FRONTEND_DEFAULT_POSITIVE_PROMPT
    form.negative_prompt = FRONTEND_DEFAULT_NEGATIVE_PROMPT
    return
  }

  if (model.default_positive_prompt) {
    form.prompt = model.default_positive_prompt
  }
  if (model.default_negative_prompt) {
    form.negative_prompt = model.default_negative_prompt
  }
}

function syncModelFromRoute() {
  const requestedModel = typeof route.query.model === 'string' ? route.query.model : ''
  if (requestedModel && generationModels.value.some((item) => item.model_name === requestedModel)) {
    form.model_name = requestedModel
  }
}

watch(
  () => route.query.model,
  () => {
    syncModelFromRoute()
  },
)

watch(
  () => platformStore.currentAssets.length,
  (count) => {
    if (activeIndex.value >= count) {
      activeIndex.value = 0
    }
  },
)

watch(
  () => platformStore.currentTask?.scoring_model_name,
  (value) => {
    if (typeof value === 'string' && value.trim()) {
      form.scoring_model_name = value
    }
  },
)

const hasWorkbenchData = computed(() => generationModels.value.length > 0 || Boolean(platformStore.currentTask))

async function bootstrapWorkbench() {
  // 首次进入页面时先准备模型列表，如果上一次任务仍在执行则继续接管轮询。
  workbenchLoading.value = !hasWorkbenchData.value
  workbenchError.value = ''

  try {
    await platformStore.fetchModels()
    syncModelFromRoute()
    if (currentModel.value) {
      fillDefaults(currentModel.value)
    }
    if (platformStore.currentTaskId) {
      await startPolling(platformStore.currentTaskId)
    }
  } catch (error) {
    workbenchError.value = platformStore.modelsLoadError || platformStore.taskLoadError || '生成工作台加载失败，请检查模型服务与任务链路。'
  } finally {
    workbenchLoading.value = false
  }
}

onMounted(() => {
  window.addEventListener('resize', syncViewport)
  void bootstrapWorkbench()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', syncViewport)
  stopPolling()
})
</script>

<template>
  <div class="workbench" :class="{ 'workbench-mobile': isMobile }">
    <el-alert v-if="workbenchError" class="workbench-alert" :closable="false" type="warning" show-icon :title="workbenchError" />

    <template v-if="workbenchLoading">
      <section class="page-skeleton"><el-skeleton animated :rows="10" /></section>
      <section class="page-skeleton"><el-skeleton animated :rows="10" /></section>
      <section class="page-skeleton"><el-skeleton animated :rows="8" /></section>
    </template>

    <template v-else>
      <ParameterPanel
        v-if="showInlineControls"
        :form="form"
        :models="generationModels"
        :scoring-models="scoringModels"
        :submitting="platformStore.submitting"
        @submit="submit"
        @fill-defaults="fillDefaults"
      />

      <div class="preview-column">
        <ResultPreview
          :assets="platformStore.currentAssets"
          :active-index="activeIndex"
          :task="platformStore.currentTask"
          @update:active-index="activeIndex = $event"
        />

        <el-button
          v-if="isMobile && workbenchSections.includes('controls')"
          class="open-parameter-button"
          type="primary"
          plain
          @click="parameterDrawerOpen = true"
        >
          打开参数面板
        </el-button>

        <GenerationProgressCard :task="platformStore.currentTask" :audit-events="platformStore.currentTaskAudit" />
      </div>

      <div class="side-column">
        <ScoreRadar :scores="activeScores" />

        <section class="status-card">
          <div class="status-header">
            <div>
              <p class="status-eyebrow">任务轨迹</p>
              <h2 class="status-title">实时状态</h2>
            </div>
            <el-tag
              v-if="platformStore.currentTask"
              :type="platformStore.currentTask.status === 'completed' ? 'success' : platformStore.currentTask.status === 'failed' ? 'danger' : 'warning'"
            >
              {{ platformStore.currentTask.stage }}
            </el-tag>
          </div>

          <el-empty v-if="!platformStore.currentTask" description="提交任务后，这里会展示实时阶段与审计轨迹。" />

          <template v-else>
            <div class="status-meta">
              <span>任务 ID #{{ platformStore.currentTask.id }}</span>
              <span>{{ platformStore.currentTask.updated_at }}</span>
            </div>

            <el-alert
              v-if="platformStore.currentTask.error_message"
              type="error"
              show-icon
              :closable="false"
              :title="platformStore.currentTask.error_message"
            />

            <div class="status-content">
              <AuditTimeline :events="platformStore.currentTaskAudit" empty-description="当前还没有可展示的审计事件。" />
            </div>
          </template>
        </section>
      </div>

      <el-drawer
        v-if="isMobile && workbenchSections.includes('controls')"
        v-model="parameterDrawerOpen"
        class="parameter-drawer"
        direction="btt"
        size="88%"
        append-to-body
      >
        <ParameterPanel
          class="panel--drawer"
          :form="form"
          :models="generationModels"
          :scoring-models="scoringModels"
          :submitting="platformStore.submitting"
          @submit="submit"
          @fill-defaults="fillDefaults"
        />
      </el-drawer>
    </template>
  </div>
</template>

<style scoped>
.workbench {
  display: grid;
  grid-template-columns: minmax(280px, 312px) minmax(0, 1fr) minmax(268px, 296px);
  gap: 16px;
  align-items: start;
}

.workbench-mobile {
  grid-template-columns: 1fr;
}

.workbench-alert {
  grid-column: 1 / -1;
}

.page-skeleton {
  border-radius: 22px;
  padding: 18px;
  background: #ffffff;
  box-shadow: var(--ea-shadow);
}

.preview-column {
  display: grid;
  gap: 16px;
  grid-template-rows: auto auto;
  align-content: start;
  min-height: 0;
}

.side-column {
  display: grid;
  gap: 16px;
  align-content: start;
  min-height: 0;
}

.status-card {
  padding: 16px;
  border-radius: 22px;
  background: #ffffff;
  box-shadow: var(--ea-shadow);
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.status-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 12px;
}

.status-eyebrow,
.status-title {
  margin: 0;
}

.status-eyebrow {
  font-size: 0.76rem;
  color: #8a5c18;
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.status-title {
  margin-top: 4px;
  color: #17202b;
  font-size: 1.18rem;
}

.status-meta {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 10px;
  color: #53606f;
  font-size: 0.82rem;
}

.status-content {
  min-height: 0;
  overflow: auto;
  padding-right: 4px;
}

.open-parameter-button {
  width: 100%;
  min-height: 44px;
  border-radius: 16px;
}

:deep(.parameter-drawer .el-drawer__header) {
  margin-bottom: 0;
  padding: 0;
}

:deep(.parameter-drawer .el-drawer__body) {
  padding: 12px 12px calc(12px + env(safe-area-inset-bottom, 0px));
}

@media (min-width: 981px) {
  .workbench {
    height: calc(100vh - 148px);
    overflow: hidden;
    align-items: stretch;
  }
}

@media (max-width: 1450px) {
  .workbench {
    grid-template-columns: minmax(280px, 304px) minmax(0, 1fr);
  }

  .side-column {
    grid-column: 1 / -1;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .status-card {
    max-height: 340px;
  }
}

@media (max-width: 980px) {
  .workbench,
  .side-column {
    grid-template-columns: 1fr;
  }

  .preview-column {
    grid-template-rows: auto;
  }
}

@media (max-width: 768px) {
  .workbench {
    grid-template-columns: 1fr;
  }

  .preview-column,
  .side-column {
    order: initial;
  }

  .status-card {
    max-height: none;
  }
}
</style>
