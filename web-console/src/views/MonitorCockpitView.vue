<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted } from 'vue'

import { usePlatformStore } from '../stores/platform'

const platformStore = usePlatformStore()

onMounted(() => {
  void platformStore.fetchMonitorOverview()
  platformStore.startMonitorStream()
})

onBeforeUnmount(() => {
  platformStore.stopMonitorStream()
})

const overview = computed(() => platformStore.monitorOverview)
const monitorHistory = computed(() => {
  const maybeHistory = (platformStore as unknown as { monitorHistory?: unknown[] }).monitorHistory
  return Array.isArray(maybeHistory) ? maybeHistory : []
})
const connectedLabel = computed(() => (platformStore.monitorConnected ? '实时连接中' : '连接已断开'))

const HEALTH_LABELS: Record<string, string> = {
  healthy: '健康',
  warning: '警告',
  critical: '严重',
}

const SERVICE_STATUS_LABELS: Record<string, string> = {
  running: '运行中',
  stopped: '已停止',
  missing: '缺失',
  degraded: '异常',
}

const STAGE_LABELS: Record<string, string> = {
  idle: '空闲',
  planning: '规划中',
  queued: '排队中',
  generating: '生成中',
  scoring: '评分中',
  completed: '已完成',
  failed: '失败',
}

const PLATFORM_LABELS: Record<string, string> = {
  macos: 'macOS',
  windows: 'Windows',
  unknown: '未知平台',
}

const ACCELERATOR_LABELS: Record<string, string> = {
  'apple-mps': 'Apple 芯片 MPS',
  'nvidia-cuda': 'NVIDIA CUDA',
  unavailable: '不可用',
}

function localizeStatus(value: string | null | undefined, mapping: Record<string, string>, fallback: string) {
  if (!value) {
    return fallback
  }
  return mapping[value] || value
}

function toPercent(used: number, total: number) {
  if (!Number.isFinite(used) || !Number.isFinite(total) || total <= 0) {
    return null
  }
  return Math.max(0, Math.min(100, Math.round((used / total) * 100)))
}

function ringPercentStyle(percent: number | null) {
  const safePercent = percent == null ? 0 : Math.max(0, Math.min(100, percent))
  return { '--ring-percent': `${safePercent}%` }
}

const cpuPercent = computed(() => {
  const cpu = overview.value?.host_snapshot?.cpu_usage_percent
  return typeof cpu === 'number' ? Math.round(cpu) : null
})

const memoryPercent = computed(() => {
  const host = overview.value?.host_snapshot
  if (!host || typeof host.memory_total_bytes !== 'number' || typeof host.memory_used_bytes !== 'number') {
    return null
  }
  return toPercent(host.memory_used_bytes, host.memory_total_bytes)
})

const acceleratorPercent = computed(() => {
  const accelerator = overview.value?.accelerator_snapshot
  if (!accelerator) {
    return null
  }
  if (typeof accelerator.gpu_utilization_percent === 'number') {
    return Math.round(accelerator.gpu_utilization_percent)
  }
  if (typeof accelerator.vram_total_mb === 'number' && typeof accelerator.vram_used_mb === 'number') {
    return toPercent(accelerator.vram_used_mb, accelerator.vram_total_mb)
  }
  return null
})

const hasMacOSMPSDetail = computed(() => {
  const accelerator = overview.value?.accelerator_snapshot
  if (!accelerator) {
    return false
  }
  const isMacOSMPS = accelerator.accelerator_type === 'apple-mps'
  const available = accelerator.available === true || accelerator.mps_available === true
  return isMacOSMPS && available
})

const acceleratorHasDetail = computed(() => acceleratorPercent.value != null || hasMacOSMPSDetail.value)

const memoryMissingReason = computed(() => {
  if (memoryPercent.value != null) {
    return ''
  }
  return '缺少 memory_total_bytes 或 memory_used_bytes'
})

const acceleratorMissingReason = computed(() => {
  const accelerator = overview.value?.accelerator_snapshot
  if (acceleratorHasDetail.value) {
    return ''
  }
  if (!accelerator) {
    return '缺少 accelerator_snapshot'
  }
  return accelerator.unavailable_reason || '缺少 gpu_utilization_percent 或 VRAM 指标'
})

const services = computed(() => overview.value?.service_snapshots ?? [])
const activeAlerts = computed(() => overview.value?.active_alerts ?? [])
const recentAlerts = computed(() => overview.value?.recent_alerts ?? [])
const taskContext = computed(() => overview.value?.task_runtime_context)
const memoryPressure = computed(() => overview.value?.host_snapshot?.memory_pressure_level || '')
const acceleratorType = computed(() => overview.value?.accelerator_snapshot?.accelerator_type || '')
const unifiedMemoryPressure = computed(() => overview.value?.accelerator_snapshot?.unified_memory_pressure || '')
const overallHealth = computed(() => overview.value?.overall_health || 'unknown')
const platformFamily = computed(() => overview.value?.host_snapshot?.platform_family || 'unknown')
const overallHealthLabel = computed(() => localizeStatus(overallHealth.value, HEALTH_LABELS, '未知'))
const platformFamilyLabel = computed(() => localizeStatus(platformFamily.value, PLATFORM_LABELS, '未知平台'))
const acceleratorTypeLabel = computed(() => localizeStatus(acceleratorType.value, ACCELERATOR_LABELS, '不可用'))
const trendSampleCount = computed(() => monitorHistory.value.length)
const latestTrendStamp = computed(() => {
  const latest = monitorHistory.value[monitorHistory.value.length - 1] as
    | { captured_at?: unknown; recorded_at?: unknown; overview?: { host_snapshot?: { captured_at?: unknown } } }
    | undefined
  if (!latest) {
    return '暂无时间戳'
  }
  if (typeof latest.captured_at === 'string' && latest.captured_at.length > 0) {
    return latest.captured_at
  }
  if (typeof latest.overview?.host_snapshot?.captured_at === 'string' && latest.overview.host_snapshot.captured_at.length > 0) {
    return latest.overview.host_snapshot.captured_at
  }
  if (typeof latest.recorded_at === 'number' && Number.isFinite(latest.recorded_at)) {
    return new Date(latest.recorded_at).toISOString()
  }
  return '暂无时间戳'
})
const runtimeSummary = computed(() => {
  const active = taskContext.value?.active_task_count ?? 0
  const stage = localizeStatus(taskContext.value?.latest_task_stage || 'idle', STAGE_LABELS, '空闲')
  return `${active} 个活跃任务 · 当前阶段 ${stage}`
})

const missingReasons = computed(() => {
  const reasons: string[] = []

  if ((taskContext.value?.active_task_count ?? 0) === 0 && !taskContext.value?.latest_task_stage) {
    reasons.push('当前没有运行任务，因此没有最新阶段上报')
  }

  if (services.value.length === 0) {
    reasons.push('尚未收到关键服务快照')
  }

  if (memoryPercent.value == null) {
    reasons.push(`内存指标缺失：${memoryMissingReason.value}`)
  }

  if (!acceleratorHasDetail.value) {
    reasons.push(`GPU/MPS 指标缺失：${acceleratorMissingReason.value}`)
  }

  return reasons
})
</script>

<template>
  <div class="monitor-cockpit">
    <header class="status-band">
      <div class="status-head">
        <p class="status-tag">全局状态带</p>
        <h1>平台运行监控中心</h1>
        <p class="status-copy">正式单页监控平台：连接态、健康级别、资源压力和执行上下文统一呈现。</p>
      </div>
      <div class="status-meta">
        <span class="pill">{{ connectedLabel }}</span>
        <div class="meta-grid">
          <div>
            <span>运行平台</span>
            <strong>{{ platformFamilyLabel }}</strong>
          </div>
          <div>
            <span>总体健康</span>
            <strong>{{ overallHealthLabel }}</strong>
          </div>
          <div>
            <span>运行态势</span>
            <strong>{{ runtimeSummary }}</strong>
          </div>
        </div>
      </div>
    </header>

    <section class="kpi-grid">
      <article class="kpi-card">
        <span>摘要指标</span>
        <strong>{{ overallHealthLabel }}</strong>
        <small>{{ connectedLabel }}</small>
      </article>
      <article class="kpi-card">
        <span>活跃任务</span>
        <strong>{{ taskContext?.active_task_count ?? 0 }}</strong>
        <small>{{ taskContext?.latest_task_stage ? localizeStatus(taskContext.latest_task_stage, STAGE_LABELS, taskContext.latest_task_stage) : '当前暂无阶段上报' }}</small>
      </article>
      <article class="kpi-card">
        <span>服务总数</span>
        <strong>{{ services.length }}</strong>
        <small>{{ services.length ? '服务矩阵已刷新' : '当前缺少服务快照' }}</small>
      </article>
      <article class="kpi-card">
        <span>活跃告警</span>
        <strong>{{ activeAlerts.length }}</strong>
        <small>{{ activeAlerts[0]?.title || '暂无活跃告警' }}</small>
      </article>
    </section>

    <section class="panel">
      <div class="section-head">
        <h2>趋势区</h2>
        <p>已接入实时历史样本，当前先展示轻量趋势摘要，后续可直接替换为折线图组件。</p>
      </div>
      <div class="trend-strip">
        <p>近 {{ trendSampleCount }} 条样本</p>
        <small>实时历史已接入 · 最新采样时间：{{ latestTrendStamp }}</small>
      </div>
    </section>

    <section class="panel">
      <div class="section-head">
        <h2>资源区</h2>
        <p>CPU、内存、GPU/MPS 三个核心资源一屏可读。</p>
      </div>
      <div class="rings">
        <article class="ring-card">
          <div class="ring-shell" :style="ringPercentStyle(cpuPercent)">
            <div class="ring-core">
              <span class="ring-value">{{ cpuPercent != null ? `${cpuPercent}%` : 'N/A' }}</span>
              <span class="ring-label">CPU</span>
            </div>
          </div>
          <h3>CPU</h3>
          <p class="ring-copy">{{ cpuPercent != null ? '当前处理器负载已成功采样。' : 'CPU 指标缺失' }}</p>
        </article>

        <article class="ring-card">
          <div class="ring-shell ring-memory" :style="ringPercentStyle(memoryPercent)">
            <div class="ring-core">
              <span class="ring-value">{{ memoryPercent != null ? `${memoryPercent}%` : 'N/A' }}</span>
              <span class="ring-label">内存</span>
            </div>
          </div>
          <h3>内存</h3>
          <p v-if="memoryPercent != null" class="ring-copy">内存压力等级：{{ memoryPressure || 'normal' }}</p>
          <p v-else class="ring-copy missing">内存指标缺失：{{ memoryMissingReason }}</p>
        </article>

        <article class="ring-card">
          <div class="ring-shell ring-accelerator" :style="ringPercentStyle(acceleratorPercent)">
            <div class="ring-core">
              <span class="ring-value">{{ acceleratorPercent != null ? `${acceleratorPercent}%` : 'N/A' }}</span>
              <span class="ring-label">GPU/MPS</span>
            </div>
          </div>
          <h3>加速器状态</h3>
          <p v-if="acceleratorHasDetail" class="ring-copy">
            {{ acceleratorTypeLabel }}<span v-if="unifiedMemoryPressure"> · 统一内存压力：{{ unifiedMemoryPressure }}</span>
          </p>
          <p v-else class="ring-copy missing">GPU/MPS 指标缺失：{{ acceleratorMissingReason }}</p>
        </article>
      </div>
    </section>

    <section class="matrix-grid">
      <article class="panel">
        <div class="section-head">
          <h2>服务矩阵</h2>
          <p>把关键服务运行状态做成矩阵卡，便于值班时快速扫读。</p>
        </div>
        <ul v-if="services.length" class="stack-list">
          <li v-for="service in services" :key="service.service_name" class="service-item">
            <strong>{{ service.service_name }}</strong>
            <span>{{ localizeStatus(service.status, SERVICE_STATUS_LABELS, service.status) }}</span>
          </li>
        </ul>
        <p v-else class="panel-copy">暂无关键服务快照</p>
      </article>

      <article class="panel">
        <div class="section-head">
          <h2>AI 运行态</h2>
          <p>展示任务与加速器运行语义，不把缺失 GPU 百分比伪造成 0%。</p>
        </div>
        <p class="panel-copy">当前阶段：{{ localizeStatus(taskContext?.latest_task_stage || 'idle', STAGE_LABELS, '空闲') }}</p>
        <p class="panel-copy">活跃任务数：{{ taskContext?.active_task_count ?? 0 }}</p>
        <p class="panel-copy">当前加速器：{{ acceleratorTypeLabel }}</p>
        <p class="panel-copy" v-if="overview?.accelerator_snapshot?.summary_label">
          {{ overview?.accelerator_snapshot?.summary_label }}
        </p>
        <p class="panel-copy" v-if="unifiedMemoryPressure">统一内存压力：{{ unifiedMemoryPressure }}</p>
      </article>
    </section>

    <section class="matrix-grid">
      <article class="panel strong-panel">
        <div class="section-head">
          <h2>告警与解释</h2>
          <p>汇总活跃告警、最近告警和字段缺失解释，确保值班信息闭环。</p>
        </div>
        <ul v-if="activeAlerts.length" class="stack-list">
          <li v-for="alert in activeAlerts" :key="alert.alert_id" class="notice-item">{{ alert.title || alert.alert_id }}</li>
        </ul>
        <p v-else class="panel-copy">暂无活跃告警</p>
        <ul v-if="recentAlerts.length" class="stack-list">
          <li v-for="alert in recentAlerts" :key="alert.alert_id" class="notice-item">{{ alert.title || alert.alert_id }}</li>
        </ul>
        <ul v-if="missingReasons.length" class="stack-list">
          <li v-for="reason in missingReasons" :key="reason" class="notice-item">{{ reason }}</li>
        </ul>
        <p v-else class="panel-copy">当前监控字段完整，没有发现缺失项。</p>
      </article>
    </section>
  </div>
</template>

<style scoped>
.monitor-cockpit {
  display: grid;
  gap: 22px;
}

.monitor-cockpit h1,
.monitor-cockpit h2,
.monitor-cockpit p,
.monitor-cockpit span,
.monitor-cockpit strong,
.monitor-cockpit small {
  margin: 0;
}

.status-band {
  display: flex;
  justify-content: space-between;
  gap: 22px;
  padding: 26px;
  border-radius: 24px;
  color: var(--ea-text);
  background:
    radial-gradient(circle at top left, rgba(29, 78, 216, 0.08), transparent 35%),
    radial-gradient(circle at right, rgba(14, 165, 233, 0.06), transparent 32%),
    linear-gradient(138deg, #ffffff 0%, #f8fafc 60%, #f1f5f9 100%);
  border: 1px solid var(--ea-border);
  box-shadow: var(--ea-shadow);
}

.status-head {
  display: grid;
  gap: 10px;
}

.status-tag {
  color: var(--ea-primary-strong);
  font-size: 0.78rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.status-head h1 {
  font-size: clamp(1.9rem, 2.8vw, 2.6rem);
  color: var(--ea-text);
}

.status-copy {
  max-width: 760px;
  color: var(--ea-text-muted);
  line-height: 1.7;
}

.status-meta {
  min-width: 300px;
  display: grid;
  align-content: start;
  justify-items: end;
  gap: 12px;
}

.pill {
  display: inline-flex;
  align-items: center;
  padding: 8px 14px;
  border-radius: 999px;
  font-size: 0.88rem;
  font-weight: 700;
  color: var(--ea-primary-strong);
  border: 1px solid rgba(29, 78, 216, 0.18);
  background: rgba(219, 234, 254, 0.72);
}

.meta-grid {
  width: 100%;
  display: grid;
  gap: 8px;
}

.meta-grid div {
  border-radius: 12px;
  padding: 10px 12px;
  background: rgba(248, 250, 252, 0.98);
  border: 1px solid var(--ea-border);
  display: grid;
  gap: 4px;
}

.meta-grid span {
  font-size: 0.74rem;
  color: var(--ea-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.meta-grid strong {
  color: var(--ea-text);
  font-size: 0.95rem;
}

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.kpi-card {
  padding: 18px 20px;
  border-radius: 22px;
  background: linear-gradient(180deg, #ffffff 0%, #f0f5fb 100%);
  box-shadow: 0 14px 35px rgba(15, 23, 42, 0.08);
}

.kpi-card span {
  display: block;
  color: #5f7087;
  font-size: 0.82rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.kpi-card strong {
  display: block;
  margin-top: 12px;
  color: #132238;
  font-size: 2rem;
  line-height: 1.1;
}

.kpi-card small {
  display: block;
  margin-top: 10px;
  color: #55657d;
  font-size: 0.92rem;
}

.panel {
  border-radius: 24px;
  background: #ffffff;
  box-shadow: 0 18px 45px rgba(15, 23, 42, 0.08);
  padding: 24px;
}

.section-head {
  display: grid;
  gap: 6px;
}

.section-head h2 {
  color: #132238;
  font-size: 1.15rem;
}

.section-head p {
  color: #64758b;
  font-size: 0.94rem;
  line-height: 1.65;
}

.trend-strip {
  margin-top: 18px;
  border-radius: 16px;
  background: linear-gradient(90deg, #eff6ff 0%, #ecfeff 100%);
  border: 1px solid #dbeafe;
  padding: 14px 16px;
  display: grid;
  gap: 4px;
}

.trend-strip p {
  color: #0f172a;
  font-size: 1.06rem;
  font-weight: 700;
}

.trend-strip small {
  color: #334155;
}

.rings {
  display: grid;
  gap: 18px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  margin-top: 18px;
}

.ring-card {
  min-height: 260px;
  padding: 22px 18px;
  border-radius: 26px;
  background: linear-gradient(180deg, #f7fbff 0%, #eef5fb 100%);
  text-align: center;
  display: grid;
  justify-items: center;
  align-content: start;
  gap: 12px;
}

.ring-shell {
  --ring-percent: 0%;
  --ring-track: #dbe7f7;
  --ring-fill-start: #1d4ed8;
  --ring-fill-end: #38bdf8;
  width: 168px;
  height: 168px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background:
    radial-gradient(circle, transparent 62%, rgba(255, 255, 255, 0.22) 63%, transparent 65%),
    conic-gradient(
      from -90deg,
      var(--ring-fill-start) 0%,
      var(--ring-fill-end) var(--ring-percent),
      var(--ring-track) var(--ring-percent) 100%
    );
  box-shadow: 0 16px 40px rgba(29, 78, 216, 0.18);
}

.ring-memory {
  --ring-fill-start: #0f9d58;
  --ring-fill-end: #7dd3fc;
  box-shadow: 0 16px 40px rgba(15, 157, 88, 0.18);
}

.ring-accelerator {
  --ring-fill-start: #f59e0b;
  --ring-fill-end: #f97316;
  box-shadow: 0 16px 40px rgba(245, 158, 11, 0.2);
}

.ring-core {
  width: 122px;
  height: 122px;
  border-radius: 50%;
  display: grid;
  align-content: center;
  justify-items: center;
  background: #ffffff;
  box-shadow: inset 0 0 0 1px rgba(19, 34, 56, 0.06);
}

.ring-value {
  color: #132238;
  font-size: 1.7rem;
  font-weight: 800;
  line-height: 1;
}

.ring-label {
  margin-top: 8px;
  color: #607188;
  font-size: 0.82rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.ring-card h3 {
  color: #132238;
  font-size: 1.05rem;
}

.ring-copy {
  color: #55657d;
  line-height: 1.6;
  font-size: 0.94rem;
}

.missing {
  color: #a23a1b;
  font-weight: 600;
}

.matrix-grid {
  display: grid;
  gap: 16px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.strong-panel {
  background: linear-gradient(180deg, #fff9f3 0%, #fffdf8 100%);
}

.stack-list {
  display: grid;
  gap: 12px;
  padding: 0;
  margin: 18px 0 0;
  list-style: none;
}

.notice-item,
.service-item {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 16px;
  border-radius: 16px;
  background: #f2f6fb;
  color: #1e2c40;
  line-height: 1.55;
}

.notice-item {
  justify-content: flex-start;
}

.service-item strong {
  color: #132238;
}

.service-item span {
  color: #4f627b;
  font-weight: 600;
}

.panel-copy {
  margin-top: 16px;
  color: #55657d;
  line-height: 1.7;
}

@media (max-width: 1180px) {
  .kpi-grid,
  .rings,
  .matrix-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 860px) {
  .status-band,
  .kpi-grid,
  .rings,
  .matrix-grid {
    grid-template-columns: 1fr;
  }

  .status-band {
    display: grid;
  }

  .status-meta {
    justify-items: start;
    min-width: 0;
  }
}
</style>
