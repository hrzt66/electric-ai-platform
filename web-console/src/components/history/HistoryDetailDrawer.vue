<script setup lang="ts">
import { computed } from 'vue'

import AuditTimeline from '../audit/AuditTimeline.vue'
import { buildImageUrl } from '../../api/platform'
import type { AssetDetail, AuditEvent } from '../../types/platform'
import { getScoreGrade } from '../../utils/score-grade'

const props = defineProps<{
  visible: boolean
  detail: AssetDetail | null
  auditEvents: AuditEvent[]
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
}>()

const scores = computed(() => {
  if (!props.detail) {
    return []
  }

  return [
    { label: '视觉保真', value: props.detail.score.visual_fidelity, grade: getScoreGrade(props.detail.score.visual_fidelity) },
    { label: '文本一致', value: props.detail.score.text_consistency, grade: getScoreGrade(props.detail.score.text_consistency) },
    { label: '物理合理', value: props.detail.score.physical_plausibility, grade: getScoreGrade(props.detail.score.physical_plausibility) },
    {
      label: '构图美学',
      value: props.detail.score.composition_aesthetics,
      grade: getScoreGrade(props.detail.score.composition_aesthetics),
    },
    { label: '总分', value: props.detail.score.total_score },
  ]
})
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
        <article v-for="score in scores" :key="score.label" class="score-chip">
          <div class="score-chip__top">
            <span>{{ score.label }}</span>
            <span v-if="score.grade" class="grade-chip" :data-grade="score.grade">{{ score.grade }}</span>
          </div>
          <strong>{{ Number(score.value).toFixed(2) }}</strong>
        </article>
      </div>

      <section class="audit">
        <div class="section-title">任务审计轨迹</div>
        <AuditTimeline :events="auditEvents" empty-description="当前没有可展示的审计事件。" />
      </section>
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
  padding: 12px;
  border-radius: 16px;
  background: #f8fafc;
  display: grid;
  gap: 8px;
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

.grade-chip[data-grade='A'] {
  color: #166534;
  background: #dcfce7;
  border-color: #86efac;
}

.grade-chip[data-grade='B'] {
  color: #1d4ed8;
  background: #dbeafe;
  border-color: #93c5fd;
}

.grade-chip[data-grade='C'] {
  color: #854d0e;
  background: #fef3c7;
  border-color: #fcd34d;
}

.grade-chip[data-grade='D'] {
  color: #b45309;
  background: #ffedd5;
  border-color: #fdba74;
}

.grade-chip[data-grade='E'] {
  color: #b91c1c;
  background: #fee2e2;
  border-color: #fca5a5;
}

.section-title {
  font-weight: 700;
  color: #17202b;
}

@media (max-width: 760px) {
  .score-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
