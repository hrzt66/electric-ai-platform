import { createSSRApp, h } from 'vue'
import { renderToString } from 'vue/server-renderer'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

type PlatformStoreMock = {
  monitorOverview: Record<string, unknown> | null
  monitorConnected: boolean
  monitorHistory?: Record<string, unknown>[]
}

const platformStore: PlatformStoreMock = {
  monitorOverview: null,
  monitorConnected: false,
  monitorHistory: [],
}

vi.mock('../stores/platform', () => ({
  usePlatformStore: () => platformStore,
}))

import MonitorCockpitView from './MonitorCockpitView.vue'

async function renderView() {
  const app = createSSRApp({
    render: () => h(MonitorCockpitView),
  })
  return renderToString(app)
}

describe('MonitorCockpitView', () => {
  beforeEach(() => {
    platformStore.monitorOverview = null
    platformStore.monitorConnected = false
    platformStore.monitorHistory = []
  })

  it('renders formal Chinese monitor homepage sections and maps status values to Chinese', async () => {
    platformStore.monitorConnected = true
    platformStore.monitorHistory = [
      { captured_at: '2026-05-03T10:00:00Z', host_snapshot: { cpu_usage_percent: 24 } },
      { captured_at: '2026-05-03T10:01:00Z', host_snapshot: { cpu_usage_percent: 30 } },
      { captured_at: '2026-05-03T10:02:00Z', host_snapshot: { cpu_usage_percent: 34 } },
    ]
    platformStore.monitorOverview = {
      overall_health: 'warning',
      host_snapshot: {
        platform_family: 'macos',
        cpu_usage_percent: 34,
        memory_total_bytes: 16000000000,
        memory_used_bytes: 8000000000,
        memory_pressure_level: 'normal',
      },
      accelerator_snapshot: {
        accelerator_type: 'apple-mps',
        gpu_utilization_percent: 56,
        unified_memory_pressure: 'warning',
      },
      service_snapshots: [
        { service_name: 'python-ai-service', status: 'running' },
        { service_name: 'python-ai-worker', status: 'degraded' },
      ],
      task_runtime_context: { active_task_count: 3, latest_task_stage: 'generating' },
      active_alerts: [{ alert_id: 'high-latency', level: 'warning', title: '推理延迟偏高' }],
      recent_alerts: [{ alert_id: 'recover', level: 'healthy', title: '服务已恢复' }],
    }

    const html = await renderView()

    expect(html).toContain('平台运行监控中心')
    expect(html).toContain('全局状态带')
    expect(html).toContain('摘要指标')
    expect(html).toContain('趋势区')
    expect(html).toContain('实时历史已接入')
    expect(html).toContain('近 3 条样本')
    expect(html).toContain('资源区')
    expect(html).toContain('服务矩阵')
    expect(html).toContain('告警与解释')
    expect(html).toContain('AI 运行态')
    expect(html).toContain('实时连接中')
    expect(html).toContain('34%')
    expect(html).toContain('50%')
    expect(html).toContain('56%')
    expect(html).toContain('python-ai-service')
    expect(html).toContain('python-ai-worker')
    expect(html).toContain('警告')
    expect(html).toContain('运行中')
    expect(html).toContain('异常')
    expect(html).toContain('活跃告警')
    expect(html).toContain('推理延迟偏高')
    expect(html).toContain('生成中')
  })

  it('renders real MPS semantics in Chinese without faking GPU percentages on macOS', async () => {
    platformStore.monitorConnected = true
    platformStore.monitorOverview = {
      overall_health: 'warning',
      host_snapshot: {
        platform_family: 'macos',
        cpu_usage_percent: 31,
        memory_total_bytes: 1600,
        memory_used_bytes: 800,
      },
      accelerator_snapshot: {
        accelerator_type: 'apple-mps',
        available: true,
        mps_available: true,
        preferred_device_type: 'mps',
        unified_memory_pressure: 'warning',
        ai_process_memory_bytes: 1073741824,
        summary_label: 'MPS available',
      },
      service_snapshots: [{ service_name: 'gateway-service', status: 'running' }],
      task_runtime_context: { active_task_count: 1, latest_task_stage: 'planning' },
      active_alerts: [],
      recent_alerts: [],
    }

    const html = await renderView()

    expect(html).toContain('加速器状态')
    expect(html).toContain('N/A')
    expect(html).toContain('Apple 芯片 MPS')
    expect(html).toContain('MPS available')
    expect(html).toContain('统一内存压力：warning')
    expect(html).not.toContain('GPU/MPS 指标缺失')
    expect(html).not.toContain('加速器状态 0%')
  })

  it('renders missing-data reasons when key monitor fields are absent', async () => {
    platformStore.monitorConnected = false
    platformStore.monitorOverview = {
      overall_health: 'warning',
      host_snapshot: {
        platform_family: 'windows',
        cpu_usage_percent: 25,
      },
      accelerator_snapshot: {
        accelerator_type: 'unavailable',
        unavailable_reason: '当前节点未检测到可用加速器',
      },
      service_snapshots: [],
      task_runtime_context: { active_task_count: 0, latest_task_stage: '' },
      active_alerts: [],
      recent_alerts: [],
    }

    const html = await renderView()

    expect(html).toContain('连接已断开')
    expect(html).toContain('告警与解释')
    expect(html).toContain('当前没有运行任务，因此没有最新阶段上报')
    expect(html).toContain('尚未收到关键服务快照')
    expect(html).toContain('内存指标缺失')
    expect(html).toContain('当前节点未检测到可用加速器')
    expect(html).toContain('GPU/MPS 指标缺失')
    expect(html).toContain('Windows')
  })

  it('loads overview data and manages the monitor stream when the page mounts', () => {
    const content = readFileSync(resolve(__dirname, './MonitorCockpitView.vue'), 'utf8')

    expect(content).toContain('onMounted')
    expect(content).toContain('platformStore.fetchMonitorOverview')
    expect(content).toContain('platformStore.startMonitorStream')
    expect(content).toContain('onBeforeUnmount')
    expect(content).toContain('platformStore.stopMonitorStream')
  })
})
