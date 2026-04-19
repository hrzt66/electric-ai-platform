<script setup lang="ts">
import { computed } from 'vue'

import type { ScoreSummary } from '../../types/platform'
import { getScoreBand } from '../../utils/score-grade'

const props = defineProps<{
  scores: ScoreSummary | null
}>()

const metrics = computed(() => [
  { label: '视觉保真', value: props.scores?.visual_fidelity ?? 0, tone: '#1d4ed8', band: getScoreBand(props.scores?.visual_fidelity ?? 0) },
  { label: '文本一致', value: props.scores?.text_consistency ?? 0, tone: '#15803d', band: getScoreBand(props.scores?.text_consistency ?? 0) },
  { label: '物理合理', value: props.scores?.physical_plausibility ?? 0, tone: '#d97706', band: getScoreBand(props.scores?.physical_plausibility ?? 0) },
  {
    label: '构图美学',
    value: props.scores?.composition_aesthetics ?? 0,
    tone: '#b91c1c',
    band: getScoreBand(props.scores?.composition_aesthetics ?? 0),
  },
])
const totalBand = computed(() => (props.scores ? getScoreBand(props.scores.total_score) : null))

function polarPoint(index: number, value: number, radius = 84) {
  const angle = (-90 + index * 90) * (Math.PI / 180)
  const ratio = Math.max(0, Math.min(value, 100)) / 100
  const x = 120 + Math.cos(angle) * radius * ratio
  const y = 120 + Math.sin(angle) * radius * ratio
  return `${x},${y}`
}

function gridPoint(index: number, level: number, radius = 84) {
  const angle = (-90 + index * 90) * (Math.PI / 180)
  const ratio = level / 100
  const x = 120 + Math.cos(angle) * radius * ratio
  const y = 120 + Math.sin(angle) * radius * ratio
  return `${x},${y}`
}

const scorePolygon = computed(() => metrics.value.map((metric, index) => polarPoint(index, metric.value)).join(' '))
const gridLevels = [20, 40, 60, 80, 100]
const metricLabels = [
  { text: '视觉保真', x: 120, y: 18 },
  { text: '文本一致', x: 212, y: 126 },
  { text: '物理合理', x: 120, y: 230 },
  { text: '构图美学', x: 28, y: 126 },
]
</script>

<template>
  <section class="score-card">
    <div class="score-header">
      <div>
        <p class="score-eyebrow">质量评估</p>
        <h2 class="score-title">四维评分雷达图</h2>
      </div>

      <div class="total">
        <span>总分</span>
        <strong>{{ scores?.total_score?.toFixed(2) ?? '--' }}</strong>
        <span v-if="totalBand" class="grade-chip total-grade" :data-grade="totalBand.key">{{ totalBand.label }}</span>
      </div>
    </div>

    <div class="radar-wrap">
      <svg viewBox="0 0 240 240" class="radar-svg" aria-label="score radar">
        <polygon
          v-for="level in gridLevels"
          :key="level"
          :points="[0, 1, 2, 3].map((index) => gridPoint(index, level)).join(' ')"
          class="grid"
        />
        <line x1="120" y1="36" x2="120" y2="204" class="axis" />
        <line x1="36" y1="120" x2="204" y2="120" class="axis" />
        <polygon :points="scorePolygon" class="shape" />
        <circle
          v-for="(metric, index) in metrics"
          :key="metric.label"
          :cx="polarPoint(index, metric.value).split(',')[0]"
          :cy="polarPoint(index, metric.value).split(',')[1]"
          r="4"
          class="dot"
        />
        <text v-for="label in metricLabels" :key="label.text" :x="label.x" :y="label.y" text-anchor="middle" class="label">
          {{ label.text }}
        </text>
      </svg>
    </div>

    <div class="metric-list">
      <div v-for="metric in metrics" :key="metric.label" class="metric-item">
        <div class="metric-top">
          <span>{{ metric.label }}</span>
          <div class="metric-value">
            <strong>{{ metric.value.toFixed(2) }}</strong>
            <span class="grade-chip" :data-grade="metric.band.key">{{ metric.band.label }}</span>
          </div>
        </div>
        <div class="metric-bar">
          <span class="metric-fill" :style="{ width: `${metric.value}%`, background: metric.tone }" />
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.score-card {
  padding: 16px;
  border-radius: 22px;
  background: #ffffff;
  box-shadow: var(--ea-shadow);
}

.score-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.score-eyebrow,
.score-title,
.total span,
.total strong {
  margin: 0;
}

.score-eyebrow {
  font-size: 0.76rem;
  color: #8a5c18;
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.score-title {
  margin-top: 4px;
  font-size: 1.18rem;
  color: #17202b;
}

.total {
  padding: 8px 12px;
  border-radius: 14px;
  background: #f8fafc;
  text-align: right;
}

.total span {
  display: block;
  color: #64748b;
  font-size: 0.74rem;
}

.total strong {
  display: block;
  font-size: 1.22rem;
  color: #17202b;
}

.total-grade {
  margin-top: 6px;
}

.radar-wrap {
  display: grid;
  place-items: center;
  margin-top: 4px;
}

.radar-svg {
  width: min(100%, 260px);
  aspect-ratio: 1;
}

.grid {
  fill: rgba(19, 71, 168, 0.03);
  stroke: rgba(23, 32, 43, 0.08);
  stroke-width: 1;
}

.axis {
  stroke: rgba(23, 32, 43, 0.15);
  stroke-width: 1;
}

.shape {
  fill: rgba(19, 71, 168, 0.2);
  stroke: #1347a8;
  stroke-width: 2;
}

.dot {
  fill: #1347a8;
}

.label {
  fill: #334155;
  font-size: 11px;
  font-weight: 600;
}

.metric-list {
  display: grid;
  gap: 8px;
}

.metric-top {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  color: #334155;
  font-size: 0.84rem;
}

.metric-value {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.metric-bar {
  margin-top: 4px;
  height: 8px;
  background: #e2e8f0;
  border-radius: 999px;
  overflow: hidden;
}

.metric-fill {
  display: block;
  height: 100%;
  border-radius: inherit;
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
</style>
