export type ApiEnvelope<T> = {
  code: number
  message: string
  data: T
  trace_id: string
}

export type GenerateTaskRequest = {
  prompt: string
  negative_prompt: string
  model_name: string
  scoring_model_name?: string
  seed: number
  steps: number
  guidance_scale: number
  width: number
  height: number
  num_images: number
}

export type GenerateTask = {
  id: number
  job_type: string
  status: string
  stage: string
  error_message: string
  model_name: string
  scoring_model_name?: string
  prompt: string
  negative_prompt: string
  payload_json: string
  created_at: string
  updated_at: string
}

export type ScoreSummary = {
  visual_fidelity: number
  text_consistency: number
  physical_plausibility: number
  composition_aesthetics: number
  total_score: number
}

export type ScoreDimensionKey =
  | 'visual_fidelity'
  | 'text_consistency'
  | 'physical_plausibility'
  | 'composition_aesthetics'
  | 'total_score'

export type ScoreExplanationDetection = {
  class_name: string
  confidence: number
  bbox?: number[]
}

export type ScoreExplanationDimension = {
  title?: string
  score?: number
  grade_label?: string
  uses_yolo: boolean
  summary: string
  formula: string
  details: string[]
  checked_image_path?: string
  expected_classes?: string[]
  matched_classes?: string[]
  missing_classes?: string[]
  detections?: ScoreExplanationDetection[]
  inputs?: Record<string, unknown>
}

export type ScoreExplanation = {
  checked_image_path?: string
  dimensions: Partial<Record<ScoreDimensionKey, ScoreExplanationDimension>>
}

export type AssetHistoryItem = ScoreSummary & {
  id: number
  job_id: number
  image_name: string
  file_path: string
  model_name: string
  status: string
  positive_prompt: string
  negative_prompt: string
  sampling_steps: number
  seed: number
  guidance_scale: number
  created_at: string
}

export type AssetHistoryPageQuery = {
  page: number
  page_size: number
  prompt_keyword?: string
  model_name?: string
  status?: string
  min_total_score?: number
}

export type AssetHistoryPage = {
  items: AssetHistoryItem[]
  page: number
  page_size: number
  total: number
  total_pages: number
}

export type AssetDetail = {
  asset: {
    id: number
    job_id: number
    image_name: string
    file_path: string
    model_name: string
    status: string
    created_at: string
    updated_at: string
  }
  prompt: {
    positive_prompt: string
    negative_prompt: string
    sampling_steps: number
    seed: number
    guidance_scale: number
  }
  score: ScoreSummary
  checked_image_path?: string
  score_explanation?: ScoreExplanation
}

export type AuditEvent = {
  id: number
  job_id: number
  event_type: string
  message: string
  payload_json: string
  created_at: string
}

export type ModelRecord = {
  id: number
  model_name: string
  display_name: string
  model_type: string
  service_name: string
  status: string
  description: string
  default_positive_prompt: string
  default_negative_prompt: string
  local_path: string
}
