<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import AuditTimeline from '../audit/AuditTimeline.vue'
import { buildImageUrl } from '../../api/platform'
import type { AssetDetail, AuditEvent, ScoreDimensionKey, ScoreExplanationDimension } from '../../types/platform'
import { getScoreBand } from '../../utils/score-grade'

const props = defineProps<{
  visible: boolean
  detail: AssetDetail | null
  auditEvents: AuditEvent[]
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
}>()

const explanationVisible = ref(false)
const activeDimensionKey = ref<ScoreDimensionKey | null>(null)
const checkedImageUrl = ref('')

const DIMENSION_LABELS: Record<ScoreDimensionKey, string> = {
  visual_fidelity: '视觉保真',
  text_consistency: '文本一致',
  physical_plausibility: '物理合理',
  composition_aesthetics: '构图美学',
  total_score: '总分',
}

const scores = computed(() => {
  if (!props.detail) {
    return []
  }

  const explanations = props.detail.score_explanation?.dimensions ?? {}
  return [
    {
      key: 'visual_fidelity' as const,
      label: '视觉保真',
      value: props.detail.score.visual_fidelity,
      band: getScoreBand(props.detail.score.visual_fidelity),
      hasExplanation: Boolean(explanations.visual_fidelity),
    },
    {
      key: 'text_consistency' as const,
      label: '文本一致',
      value: props.detail.score.text_consistency,
      band: getScoreBand(props.detail.score.text_consistency),
      hasExplanation: Boolean(explanations.text_consistency),
    },
    {
      key: 'physical_plausibility' as const,
      label: '物理合理',
      value: props.detail.score.physical_plausibility,
      band: getScoreBand(props.detail.score.physical_plausibility),
      hasExplanation: Boolean(explanations.physical_plausibility),
    },
    {
      key: 'composition_aesthetics' as const,
      label: '构图美学',
      value: props.detail.score.composition_aesthetics,
      band: getScoreBand(props.detail.score.composition_aesthetics),
      hasExplanation: Boolean(explanations.composition_aesthetics),
    },
    {
      key: 'total_score' as const,
      label: '总分',
      value: props.detail.score.total_score,
      band: getScoreBand(props.detail.score.total_score),
      hasExplanation: Boolean(explanations.total_score),
    },
  ]
})

const hasAnyExplanation = computed(() => Boolean(props.detail?.score_explanation?.dimensions && Object.keys(props.detail.score_explanation.dimensions).length > 0))

const activeExplanation = computed<ScoreExplanationDimension | null>(() => {
  if (!props.detail || !activeDimensionKey.value) {
    return null
  }
  return props.detail.score_explanation?.dimensions?.[activeDimensionKey.value] ?? null
})

const activeScore = computed(() => scores.value.find((item) => item.key === activeDimensionKey.value) ?? null)

const activeDimensionTitle = computed(() => {
  if (!activeDimensionKey.value) {
    return '评分说明'
  }
  return DIMENSION_LABELS[activeDimensionKey.value]
})

const activeCheckedImagePath = computed(() => {
  return (
    activeExplanation.value?.checked_image_path ||
    props.detail?.checked_image_path ||
    props.detail?.score_explanation?.checked_image_path ||
    guessCheckedImagePath(props.detail?.asset.file_path ?? '')
  )
})

const activeInputRows = computed(() => {
  const inputs = activeExplanation.value?.inputs ?? {}
  return Object.entries(inputs).map(([key, value]) => ({
    key,
    value: formatInputValue(value),
  }))
})

watch(
  () => props.visible,
  (visible) => {
    if (!visible) {
      explanationVisible.value = false
      activeDimensionKey.value = null
    }
  },
)

watch(
  () => props.detail,
  async (detail) => {
    checkedImageUrl.value = ''
    const candidatePath =
      detail?.checked_image_path ||
      detail?.score_explanation?.checked_image_path ||
      guessCheckedImagePath(detail?.asset.file_path ?? '')
    if (!candidatePath) {
      return
    }

    const candidateUrl = buildImageUrl(candidatePath)
    try {
      const response = await fetch(candidateUrl, { method: 'HEAD' })
      if (response.ok) {
        checkedImageUrl.value = candidateUrl
      }
    } catch {
      checkedImageUrl.value = ''
    }
  },
  { immediate: true },
)

function openExplanation(key: ScoreDimensionKey) {
  if (!props.detail?.score_explanation?.dimensions?.[key]) {
    return
  }
  activeDimensionKey.value = key
  explanationVisible.value = true
}

function formatBandRange(score: number) {
  const band = getScoreBand(score)
  const upperBound = band.maxExclusive === null ? '100' : (band.maxExclusive - 0.01).toFixed(2)
  return `${band.label}（${band.min}-${upperBound}）`
}

function formatInputValue(value: unknown): string {
  if (Array.isArray(value)) {
    return value.map((item) => formatInputValue(item)).join('；')
  }
  if (value && typeof value === 'object') {
    return Object.entries(value as Record<string, unknown>)
      .map(([key, item]) => `${key}: ${formatInputValue(item)}`)
      .join('；')
  }
  return String(value)
}

function guessCheckedImagePath(filePath: string): string {
  if (!filePath) {
    return ''
  }
  return filePath.replace(/([\\/])image([\\/])/, '$1image_check$2')
}
</script>

<template>
  <el-drawer :model-value="visible" size="720px" @update:model-value="emit('update:visible', $event)">
    <template #header>
      <div class="drawer-header">
        <div>
          <p class="drawer-eyebrow">资产详情</p>
          <h2 class="drawer-title">{{ detail?.asset.image_name ?? '结果详情' }}</h2>
        </div>
        <el-tag v-if="detail">{{ detail.asset.model_name }}</el-tag>
      </div>
    </template>

    <div v-if="detail" class="drawer-body">
      <el-image class="drawer-image" :src="buildImageUrl(detail.asset.file_path)" fit="cover" :preview-src-list="[buildImageUrl(detail.asset.file_path)]" />

      <el-descriptions :column="1" border class="drawer-descriptions">
        <el-descriptions-item label="任务 ID">{{ detail.asset.job_id }}</el-descriptions-item>
        <el-descriptions-item label="正向提示词">{{ detail.prompt.positive_prompt }}</el-descriptions-item>
        <el-descriptions-item label="负向提示词">{{ detail.prompt.negative_prompt || '无' }}</el-descriptions-item>
        <el-descriptions-item label="采样参数">
          Steps {{ detail.prompt.sampling_steps }} / Seed {{ detail.prompt.seed }} / CFG {{ detail.prompt.guidance_scale }}
        </el-descriptions-item>
      </el-descriptions>

      <div class="score-grid">
        <button
          v-for="score in scores"
          :key="score.label"
          type="button"
          class="score-chip"
          :class="{ 'score-chip--interactive': score.hasExplanation, 'score-chip--disabled': !score.hasExplanation }"
          :aria-label="`查看${score.label}评分依据`"
          :disabled="!score.hasExplanation"
          @click="openExplanation(score.key)"
        >
          <div class="score-chip__top">
            <span>{{ score.label }}</span>
            <span v-if="score.band" class="grade-chip" :data-grade="score.band.key">{{ score.band.label }}</span>
          </div>
          <strong>{{ Number(score.value).toFixed(2) }}</strong>
        </button>
      </div>

      <div v-if="!hasAnyExplanation" class="score-explanation-empty">该记录生成时未保存评分说明。</div>

      <section class="audit">
        <div class="section-title">任务审计轨迹</div>
        <AuditTimeline :events="auditEvents" empty-description="当前没有可展示的审计事件。" />
      </section>

      <el-dialog v-model="explanationVisible" width="760px" :title="`${activeDimensionTitle}评分说明`">
        <div v-if="activeExplanation && activeScore" class="explanation-panel">
          <section class="explanation-summary">
            <div class="explanation-summary__head">
              <strong>{{ activeDimensionTitle }}</strong>
              <span>{{ formatBandRange(activeScore.value) }}</span>
            </div>
            <p>{{ activeExplanation.summary }}</p>
          </section>

          <section class="explanation-block">
            <div class="section-title">评分公式</div>
            <p class="formula-text">{{ activeExplanation.formula }}</p>
          </section>

          <section class="explanation-block">
            <div class="section-title">详细依据</div>
            <ul class="detail-list">
              <li v-for="item in activeExplanation.details" :key="item">{{ item }}</li>
            </ul>
          </section>

          <section v-if="activeInputRows.length > 0" class="explanation-block">
            <div class="section-title">关键输入</div>
            <dl class="input-grid">
              <div v-for="row in activeInputRows" :key="row.key" class="input-grid__item">
                <dt>{{ row.key }}</dt>
                <dd>{{ row.value }}</dd>
              </div>
            </dl>
          </section>

          <section v-if="activeExplanation.uses_yolo" class="explanation-block">
            <div class="section-title">YOLO 检测依据</div>
            <el-image
              v-if="checkedImageUrl || activeCheckedImagePath"
              class="checked-image"
              :src="checkedImageUrl || buildImageUrl(activeCheckedImagePath)"
              fit="cover"
              :preview-src-list="[checkedImageUrl || buildImageUrl(activeCheckedImagePath)]"
            />
            <div class="tag-groups">
              <div v-if="activeExplanation.expected_classes?.length" class="tag-group">
                <span class="tag-group__label">期望对象</span>
                <el-tag v-for="item in activeExplanation.expected_classes" :key="`expected-${item}`" effect="plain">{{ item }}</el-tag>
              </div>
              <div v-if="activeExplanation.matched_classes?.length" class="tag-group">
                <span class="tag-group__label">已匹配</span>
                <el-tag v-for="item in activeExplanation.matched_classes" :key="`matched-${item}`" type="success">{{ item }}</el-tag>
              </div>
              <div v-if="activeExplanation.missing_classes?.length" class="tag-group">
                <span class="tag-group__label">缺失对象</span>
                <el-tag v-for="item in activeExplanation.missing_classes" :key="`missing-${item}`" type="danger">{{ item }}</el-tag>
              </div>
            </div>
            <ul v-if="activeExplanation.detections?.length" class="detail-list">
              <li v-for="item in activeExplanation.detections" :key="`${item.class_name}-${item.confidence}`">
                检测到 {{ item.class_name }}，置信度 {{ Number(item.confidence).toFixed(3) }}
              </li>
            </ul>
          </section>
        </div>
      </el-dialog>
    </div>
  </el-drawer>
</template>

<style scoped>
.drawer-header {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  align-items: flex-start;
}

.drawer-eyebrow,
.drawer-title {
  margin: 0;
}

.drawer-eyebrow {
  font-size: 0.8rem;
  color: #8a5c18;
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.drawer-title {
  margin-top: 6px;
  color: #17202b;
  font-size: 1.4rem;
}

.drawer-body {
  display: grid;
  gap: 18px;
}

.drawer-image {
  width: 100%;
  border-radius: 18px;
  min-height: 320px;
  background: #edf2f7;
}

.score-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 10px;
}

.score-chip {
  border: none;
  padding: 12px;
  border-radius: 16px;
  background: #f8fafc;
  display: grid;
  gap: 8px;
  text-align: left;
}

.score-chip--interactive {
  cursor: pointer;
  transition: transform 0.15s ease, box-shadow 0.15s ease, background 0.15s ease;
}

.score-chip--interactive:hover {
  background: #eef4ff;
  box-shadow: 0 10px 24px rgba(14, 76, 146, 0.08);
  transform: translateY(-1px);
}

.score-chip--disabled {
  cursor: default;
  opacity: 0.85;
}

.score-chip__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.score-chip span {
  color: #64748b;
  font-size: 0.84rem;
}

.score-chip strong {
  color: #17202b;
  font-size: 1.05rem;
}

.grade-chip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 24px;
  height: 24px;
  padding: 0 8px;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  border: 1px solid transparent;
}

.grade-chip[data-grade='excellent'] {
  color: #166534;
  background: #dcfce7;
  border-color: #86efac;
}

.grade-chip[data-grade='good'] {
  color: #1d4ed8;
  background: #dbeafe;
  border-color: #93c5fd;
}

.grade-chip[data-grade='qualified'] {
  color: #854d0e;
  background: #fef3c7;
  border-color: #fcd34d;
}

.grade-chip[data-grade='weak'] {
  color: #b45309;
  background: #ffedd5;
  border-color: #fdba74;
}

.grade-chip[data-grade='poor'] {
  color: #b91c1c;
  background: #fee2e2;
  border-color: #fca5a5;
}

.section-title {
  font-weight: 700;
  color: #17202b;
}

.score-explanation-empty {
  padding: 12px 14px;
  border-radius: 14px;
  background: #fff7ed;
  color: #9a3412;
  font-size: 0.92rem;
}

.explanation-panel {
  display: grid;
  gap: 18px;
}

.explanation-summary {
  padding: 16px;
  border-radius: 16px;
  background: linear-gradient(135deg, #eff6ff, #f8fafc);
}

.explanation-summary__head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  margin-bottom: 8px;
}

.explanation-summary__head strong {
  color: #17202b;
  font-size: 1rem;
}

.explanation-summary__head span {
  color: #475569;
  font-size: 0.88rem;
}

.explanation-summary p,
.formula-text {
  margin: 0;
  color: #334155;
  line-height: 1.7;
}

.explanation-block {
  display: grid;
  gap: 10px;
}

.detail-list {
  margin: 0;
  padding-left: 18px;
  color: #334155;
  line-height: 1.7;
}

.input-grid {
  display: grid;
  gap: 10px;
  margin: 0;
}

.input-grid__item {
  display: grid;
  gap: 4px;
  padding: 12px;
  border-radius: 14px;
  background: #f8fafc;
}

.input-grid__item dt {
  font-weight: 700;
  color: #1e293b;
}

.input-grid__item dd {
  margin: 0;
  color: #475569;
  white-space: pre-wrap;
  word-break: break-word;
}

.checked-image {
  width: 100%;
  min-height: 280px;
  border-radius: 16px;
  background: #edf2f7;
}

.tag-groups {
  display: grid;
  gap: 12px;
}

.tag-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.tag-group__label {
  min-width: 72px;
  color: #475569;
  font-size: 0.88rem;
}

@media (max-width: 760px) {
  .score-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
