import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { AssetHistoryItem, GenerateTask, GenerateTaskRequest, ModelRecord } from '../types/platform'

const api = vi.hoisted(() => ({
  createGenerateTask: vi.fn(),
  getTask: vi.fn(),
  listAssetHistory: vi.fn(),
  listAssetHistoryPage: vi.fn(),
  listModels: vi.fn(),
  listTasks: vi.fn(),
  getAssetDetail: vi.fn(),
  listTaskAuditEvents: vi.fn(),
}))

vi.mock('../api/platform', () => api)

function createDeferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (reason?: unknown) => void
  const promise = new Promise<T>((nextResolve, nextReject) => {
    resolve = nextResolve
    reject = nextReject
  })

  return { promise, resolve, reject }
}

describe('platform store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('stores the current task after submit succeeds', async () => {
    const { usePlatformStore } = await import('./platform')
    const store = usePlatformStore()
    const createdTask: GenerateTask = {
      id: 9,
      job_type: 'generate',
      status: 'queued',
      stage: 'queued',
      error_message: '',
      model_name: 'sd15-electric',
      prompt: 'substation',
      negative_prompt: 'blurry',
      payload_json: '{}',
      created_at: '2026-04-05T16:00:00+08:00',
      updated_at: '2026-04-05T16:00:00+08:00',
    }

    api.createGenerateTask.mockResolvedValue(createdTask)

    await store.submitGenerateJob({
      prompt: 'substation',
      negative_prompt: 'blurry',
      model_name: 'sd15-electric',
      seed: 1,
      steps: 12,
      guidance_scale: 7,
      width: 512,
      height: 512,
      num_images: 1,
    } satisfies GenerateTaskRequest)

    expect(store.currentTask?.id).toBe(9)
    expect(store.currentTask?.status).toBe('queued')
  })

  it('submits the requested scoring model name with the generation job payload', async () => {
    const { usePlatformStore } = await import('./platform')
    const store = usePlatformStore()
    const createdTask: GenerateTask = {
      id: 10,
      job_type: 'generate',
      status: 'queued',
      stage: 'queued',
      error_message: '',
      model_name: 'sd15-electric',
      scoring_model_name: 'electric-score-v2',
      prompt: 'substation',
      negative_prompt: 'blurry',
      payload_json: '{}',
      created_at: '2026-04-05T16:00:00+08:00',
      updated_at: '2026-04-05T16:00:00+08:00',
    }

    api.createGenerateTask.mockResolvedValue(createdTask)

    await store.submitGenerateJob({
      prompt: 'substation',
      negative_prompt: 'blurry',
      model_name: 'sd15-electric',
      scoring_model_name: 'electric-score-v2',
      seed: 1,
      steps: 12,
      guidance_scale: 7,
      width: 512,
      height: 512,
      num_images: 1,
    } satisfies GenerateTaskRequest)

    expect(api.createGenerateTask).toHaveBeenCalledWith(
      expect.objectContaining({
        scoring_model_name: 'electric-score-v2',
      }),
    )
    expect(store.currentTask?.scoring_model_name).toBe('electric-score-v2')
  })

  it('hydrates current assets from history when the task completes', async () => {
    const { usePlatformStore } = await import('./platform')
    const store = usePlatformStore()

    api.getTask.mockResolvedValue({
      id: 12,
      job_type: 'generate',
      status: 'completed',
      stage: 'completed',
      error_message: '',
      model_name: 'sd15-electric',
      prompt: 'robot',
      negative_prompt: '',
      payload_json: '{}',
      created_at: '2026-04-05T16:00:00+08:00',
      updated_at: '2026-04-05T16:01:00+08:00',
    } satisfies GenerateTask)

    api.listAssetHistory.mockResolvedValue([
      {
        id: 3,
        job_id: 12,
        image_name: '12_0_1.png',
        file_path: 'model/image/12_0_1.png',
        model_name: 'sd15-electric',
        status: 'scored',
        positive_prompt: 'robot',
        negative_prompt: '',
        sampling_steps: 12,
        seed: 1,
        guidance_scale: 7,
        visual_fidelity: 50,
        text_consistency: 51,
        physical_plausibility: 52,
        composition_aesthetics: 53,
        total_score: 51.5,
        created_at: '2026-04-05T16:01:00+08:00',
      },
      {
        id: 2,
        job_id: 11,
        image_name: '11_0_1.png',
        file_path: 'model/image/11_0_1.png',
        model_name: 'sd15-electric',
        status: 'scored',
        positive_prompt: 'other',
        negative_prompt: '',
        sampling_steps: 12,
        seed: 2,
        guidance_scale: 7,
        visual_fidelity: 60,
        text_consistency: 61,
        physical_plausibility: 62,
        composition_aesthetics: 63,
        total_score: 61.5,
        created_at: '2026-04-05T15:59:00+08:00',
      },
    ] satisfies AssetHistoryItem[])

    await store.refreshTask(12)

    expect(store.currentTask?.status).toBe('completed')
    expect(store.currentAssets).toHaveLength(1)
    expect(store.currentAssets[0].job_id).toBe(12)
  })

  it('deduplicates repeated history rows for the same generated image in the current task view', async () => {
    const { usePlatformStore } = await import('./platform')
    const store = usePlatformStore()

    api.getTask.mockResolvedValue({
      id: 12,
      job_type: 'generate',
      status: 'completed',
      stage: 'completed',
      error_message: '',
      model_name: 'sd15-electric',
      prompt: 'robot',
      negative_prompt: '',
      payload_json: '{}',
      created_at: '2026-04-05T16:00:00+08:00',
      updated_at: '2026-04-05T16:01:00+08:00',
    } satisfies GenerateTask)

    api.listAssetHistory.mockResolvedValue([
      {
        id: 5,
        job_id: 12,
        image_name: '12_0_123.png',
        file_path: 'model/image/12_0_123.png',
        model_name: 'sd15-electric',
        status: 'scored',
        positive_prompt: 'robot',
        negative_prompt: '',
        sampling_steps: 12,
        seed: 123,
        guidance_scale: 7,
        visual_fidelity: 50,
        text_consistency: 51,
        physical_plausibility: 52,
        composition_aesthetics: 53,
        total_score: 51.5,
        created_at: '2026-04-05T16:01:01+08:00',
      },
      {
        id: 3,
        job_id: 12,
        image_name: '12_0_123.png',
        file_path: 'model/image/12_0_123.png',
        model_name: 'sd15-electric',
        status: 'scored',
        positive_prompt: 'robot',
        negative_prompt: '',
        sampling_steps: 12,
        seed: 123,
        guidance_scale: 7,
        visual_fidelity: 50,
        text_consistency: 51,
        physical_plausibility: 52,
        composition_aesthetics: 53,
        total_score: 51.5,
        created_at: '2026-04-05T16:01:00+08:00',
      },
    ] satisfies AssetHistoryItem[])

    await store.refreshTask(12)

    expect(store.currentAssets).toHaveLength(1)
    expect(store.currentAssets[0].image_name).toBe('12_0_123.png')
  })

  it('refreshes audit events even before the task completes', async () => {
    const { usePlatformStore } = await import('./platform')
    const store = usePlatformStore()

    api.getTask.mockResolvedValue({
      id: 18,
      job_type: 'generate',
      status: 'generating',
      stage: 'generating',
      error_message: '',
      model_name: 'unipic2-kontext',
      prompt: 'substation robot',
      negative_prompt: '',
      payload_json: '{}',
      created_at: '2026-04-05T16:00:00+08:00',
      updated_at: '2026-04-05T16:02:00+08:00',
    } satisfies GenerateTask)

    api.listTaskAuditEvents.mockResolvedValue([
      {
        id: 1,
        job_id: 18,
        event_type: 'job_generating',
        message: 'worker started generation',
        payload_json: '',
        created_at: '2026-04-05T16:02:00+08:00',
      },
    ])

    await store.refreshTask(18)

    expect(store.currentTask?.status).toBe('generating')
    expect(store.currentTaskAudit).toHaveLength(1)
    expect(store.currentTaskAudit[0].event_type).toBe('job_generating')
  })

  it('reuses the in-flight model request during rapid page switches', async () => {
    const { usePlatformStore } = await import('./platform')
    const store = usePlatformStore()
    const inflight = createDeferred<ModelRecord[]>()

    api.listModels.mockReturnValue(inflight.promise)

    const firstLoad = store.fetchModels()
    const secondLoad = store.fetchModels()

    expect(api.listModels).toHaveBeenCalledTimes(1)

    inflight.resolve([
      {
        id: 1,
        model_name: 'sd15-electric',
        display_name: 'SD 1.5 Electric',
        model_type: 'generation',
        service_name: 'model-service',
        local_path: 'model/generation/sd15-electric',
        description: '本机扩散生成模型',
        default_positive_prompt: 'substation',
        default_negative_prompt: 'blurry',
        status: 'available',
        updated_at: '2026-04-05T16:10:00+08:00',
      },
    ])

    await Promise.all([firstLoad, secondLoad])

    expect(store.models).toHaveLength(1)
    expect(store.models[0].model_name).toBe('sd15-electric')
    expect(store.models[0].display_name).toBe('SD 1.5 电力基础版')
    expect(store.models[0].description).toContain('电力场景')
  })

  it('returns cached history during quick revisits instead of refetching immediately', async () => {
    const { usePlatformStore } = await import('./platform')
    const store = usePlatformStore()

    api.listAssetHistory.mockResolvedValue([
      {
        id: 31,
        job_id: 22,
        image_name: '22_0_1.png',
        file_path: 'model/image/22_0_1.png',
        model_name: 'sd15-electric',
        status: 'scored',
        positive_prompt: 'substation robot',
        negative_prompt: '',
        sampling_steps: 12,
        seed: 3,
        guidance_scale: 7,
        visual_fidelity: 60,
        text_consistency: 61,
        physical_plausibility: 62,
        composition_aesthetics: 63,
        total_score: 61.5,
        created_at: '2026-04-05T16:05:00+08:00',
      },
    ] satisfies AssetHistoryItem[])

    await store.fetchHistory()
    await store.fetchHistory()

    expect(api.listAssetHistory).toHaveBeenCalledTimes(1)
    expect(store.history).toHaveLength(1)
  })

  it('keeps history as an empty array when the backend responds with null', async () => {
    const { usePlatformStore } = await import('./platform')
    const store = usePlatformStore()

    api.listAssetHistory.mockResolvedValue(null)

    await store.fetchHistory()

    expect(store.history).toEqual([])
    expect(store.currentAssets).toEqual([])
  })

  it('fetches paged history with filters and stores pagination metadata', async () => {
    const { usePlatformStore } = await import('./platform')
    const store = usePlatformStore()

    api.listAssetHistoryPage.mockResolvedValue({
      items: [
        {
          id: 12,
          job_id: 8,
          image_name: '8_0_1.png',
          file_path: 'model/image/8_0_1.png',
          model_name: 'ssd1b-electric',
          status: 'scored',
          positive_prompt: 'tower line',
          negative_prompt: '',
          sampling_steps: 20,
          seed: 8,
          guidance_scale: 7,
          visual_fidelity: 72,
          text_consistency: 70,
          physical_plausibility: 68,
          composition_aesthetics: 74,
          total_score: 71,
          created_at: '2026-04-19T18:20:00+08:00',
        },
      ],
      page: 2,
      page_size: 20,
      total: 42,
      total_pages: 3,
    })

    await store.fetchHistoryPage({
      page: 2,
      page_size: 20,
      prompt_keyword: 'tower',
      model_name: 'ssd1b-electric',
      status: 'scored',
      min_total_score: 60,
    })

    expect(api.listAssetHistoryPage).toHaveBeenCalledWith({
      page: 2,
      page_size: 20,
      prompt_keyword: 'tower',
      model_name: 'ssd1b-electric',
      status: 'scored',
      min_total_score: 60,
    })
    expect(store.historyPageItems).toHaveLength(1)
    expect(store.historyPage).toBe(2)
    expect(store.historyPageSize).toBe(20)
    expect(store.historyTotal).toBe(42)
    expect(store.historyTotalPages).toBe(3)
  })

  it('keeps task audit as an empty array when the backend responds with null', async () => {
    const { usePlatformStore } = await import('./platform')
    const store = usePlatformStore()

    api.getTask.mockResolvedValue({
      id: 21,
      job_type: 'generate',
      status: 'generating',
      stage: 'generating',
      error_message: '',
      model_name: 'sd15-electric',
      prompt: 'yard overview',
      negative_prompt: '',
      payload_json: '{}',
      created_at: '2026-04-05T16:20:00+08:00',
      updated_at: '2026-04-05T16:21:00+08:00',
    } satisfies GenerateTask)
    api.listTaskAuditEvents.mockResolvedValue(null)

    await store.refreshTask(21)

    expect(store.currentTaskAudit).toEqual([])
  })
})
