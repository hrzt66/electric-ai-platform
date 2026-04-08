<script setup lang="ts">
import { computed } from 'vue'

import type { AuditEvent, GenerateTask } from '../../types/platform'
import { buildGenerationProgress, formatAuditEventLabel, getRecentAuditEvents } from './generation-progress'

const props = defineProps<{
  task: GenerateTask | null
  auditEvents: AuditEvent[]
}>()

// 进度对象把任务状态和审计事件汇总成可直接渲染的结构。
const progress = computed(() => buildGenerationProgress(props.task, props.auditEvents))
// 最近事件只展示少量条目，避免进度卡片内容过长。
const recentEvents = computed(() => getRecentAuditEvents(props.auditEvents, 2))
</script>

<template>
  <section class="progress-card progress-card--compact">
    <template v-if="progress">
      <div class="progress-header">
        <div>
          <p class="progress-eyebrow">运行跟踪</p>
          <h2 class="progress-title">生成进度</h2>
        </div>

        <div class="progress-badge" :class="`tone-${progress.tone}`">
          <strong>{{ progress.percent }}%</strong>
          <span>{{ progress.stageLabel }}</span>
        </div>
      </div>

      <div class="progress-meter">
        <div class="progress-track">
          <div class="progress-fill" :class="`tone-${progress.tone}`" :style="{ width: `${progress.percent}%` }" />
        </div>

        <div class="progress-copy">
          <strong>{{ progress.headline }}</strong>
          <span>{{ progress.detail }}</span>
        </div>
      </div>

      <div class="phase-grid">
        <article v-for="(phase, index) in progress.phases" :key="phase.key" class="phase-card" :class="`state-${phase.state}`">
          <span class="phase-index">{{ index + 1 }}</span>
          <strong>{{ phase.label }}</strong>
        </article>
      </div>

      <div v-if="recentEvents.length > 0" class="event-strip">
        <article v-for="event in recentEvents" :key="event.id" class="event-chip">
          <span class="event-time">{{ event.created_at }}</span>
          <strong>{{ formatAuditEventLabel(event.event_type) }}</strong>
        </article>
      </div>

      <div class="progress-footer">
        <span>最近更新 {{ progress.updatedAt }}</span>
        <span v-if="task">模型 {{ task.model_name }}</span>
      </div>
    </template>

    <el-empty v-else description="提交任务后，这里会显示当前生成进度和关键阶段。" />
  </section>
</template>

<style scoped>
.progress-card {
  padding: 16px;
  border-radius: 22px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
  box-shadow: var(--ea-shadow);
}

.progress-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.progress-eyebrow,
.progress-title,
.progress-copy strong,
.progress-copy span,
.phase-card strong,
.event-chip strong,
.event-time,
.progress-footer span {
  margin: 0;
}

.progress-eyebrow {
  font-size: 0.76rem;
  color: #8a5c18;
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.progress-title {
  margin-top: 4px;
  color: #17202b;
  font-size: 1.2rem;
}

.progress-badge {
  min-width: 96px;
  padding: 10px 12px;
  border-radius: 14px;
  display: grid;
  justify-items: end;
  background: #eff3f7;
}

.progress-badge strong {
  font-size: 1.18rem;
  line-height: 1;
}

.progress-badge span {
  margin-top: 4px;
  font-size: 0.8rem;
}

.progress-meter {
  margin-top: 12px;
  display: grid;
  gap: 8px;
}

.progress-track {
  height: 10px;
  border-radius: 999px;
  overflow: hidden;
  background: #dbe4ee;
}

.progress-fill {
  height: 100%;
  border-radius: inherit;
  transition: width 0.35s ease;
}

.progress-copy {
  display: grid;
  gap: 4px;
}

.progress-copy strong {
  color: #17202b;
  font-size: 0.95rem;
}

.progress-copy span {
  color: #53606f;
  line-height: 1.4;
  font-size: 0.84rem;
}

.phase-grid {
  margin-top: 12px;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}

.phase-card {
  padding: 10px;
  border-radius: 14px;
  display: grid;
  gap: 8px;
  border: 1px solid #e5edf5;
  background: rgba(255, 255, 255, 0.78);
}

.phase-index {
  width: 24px;
  height: 24px;
  border-radius: 999px;
  display: inline-grid;
  place-items: center;
  font-size: 0.8rem;
  font-weight: 700;
  background: #e5edf5;
  color: #53606f;
}

.phase-card strong {
  color: #223246;
  font-size: 0.82rem;
  line-height: 1.35;
}

.state-done {
  border-color: rgba(37, 99, 235, 0.16);
  background: rgba(37, 99, 235, 0.08);
}

.state-done .phase-index {
  background: #2557c0;
  color: #ffffff;
}

.state-active {
  border-color: rgba(212, 136, 4, 0.24);
  background: rgba(212, 136, 4, 0.08);
}

.state-active .phase-index {
  background: #d48804;
  color: #ffffff;
}

.state-failed {
  border-color: rgba(200, 51, 46, 0.2);
  background: rgba(200, 51, 46, 0.08);
}

.state-failed .phase-index {
  background: #c8332e;
  color: #ffffff;
}

.event-strip {
  margin-top: 12px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.event-chip {
  min-width: 0;
  flex: 1 1 160px;
  padding: 10px 12px;
  border-radius: 14px;
  background: #f3f6fa;
  display: grid;
  gap: 3px;
}

.event-time {
  color: #7b8794;
  font-size: 0.74rem;
}

.event-chip strong {
  color: #223246;
  font-size: 0.84rem;
}

.progress-footer {
  margin-top: 12px;
  display: flex;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
  color: #53606f;
  font-size: 0.78rem;
}

.tone-info {
  background: linear-gradient(90deg, #5b8def 0%, #7ea7f4 100%);
  color: #2557c0;
}

.tone-warning {
  background: linear-gradient(90deg, #d48804 0%, #e6a117 100%);
  color: #8a5c18;
}

.tone-success {
  background: linear-gradient(90deg, #2d9a52 0%, #58be78 100%);
  color: #2d9a52;
}

.tone-danger {
  background: linear-gradient(90deg, #c8332e 0%, #dd6156 100%);
  color: #c8332e;
}

.progress-badge.tone-info,
.progress-badge.tone-warning,
.progress-badge.tone-success,
.progress-badge.tone-danger {
  background-image: none;
}

.progress-badge.tone-info {
  background: rgba(91, 141, 239, 0.12);
}

.progress-badge.tone-warning {
  background: rgba(212, 136, 4, 0.14);
}

.progress-badge.tone-success {
  background: rgba(45, 154, 82, 0.12);
}

.progress-badge.tone-danger {
  background: rgba(200, 51, 46, 0.12);
}

@media (max-width: 920px) {
  .phase-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .progress-header {
    flex-direction: column;
    align-items: stretch;
  }

  .progress-badge {
    justify-items: start;
  }

  .phase-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .progress-card--compact {
    padding: 12px;
    border-radius: var(--ea-mobile-card-radius);
    box-shadow: var(--ea-mobile-card-shadow);
  }

  .progress-header {
    flex-direction: column;
    align-items: stretch;
  }

  .progress-badge {
    justify-items: start;
  }

  .phase-card {
    padding: 8px;
    gap: 6px;
  }

  .event-strip {
    display: grid;
    gap: 6px;
  }

  .event-chip {
    padding: 8px 10px;
    flex: initial;
  }
}
</style>
