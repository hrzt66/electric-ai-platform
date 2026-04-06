<script setup lang="ts">
import { computed } from 'vue'

import AuditTimeline from '../audit/AuditTimeline.vue'
import { buildImageUrl } from '../../api/platform'
import type { AssetDetail, AuditEvent } from '../../types/platform'

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
    ['视觉保真', props.detail.score.visual_fidelity],
    ['文本一致', props.detail.score.text_consistency],
    ['物理合理', props.detail.score.physical_plausibility],
    ['构图美学', props.detail.score.composition_aesthetics],
    ['总分', props.detail.score.total_score],
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
        <article v-for="[label, value] in scores" :key="label" class="score-chip">
          <span>{{ label }}</span>
          <strong>{{ Number(value).toFixed(2) }}</strong>
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
  gap: 6px;
}

.score-chip span {
  color: #64748b;
  font-size: 0.84rem;
}

.score-chip strong {
  color: #17202b;
  font-size: 1.05rem;
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
