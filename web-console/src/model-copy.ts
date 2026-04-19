import type { ModelRecord } from './types/platform'

type LocalizedModelCopy = {
  display_name: string
  description: string
}

const LOCALIZED_MODEL_COPY: Record<string, LocalizedModelCopy> = {
  'sd15-electric': {
    display_name: 'SD 1.5 电力基础版',
    description: '面向电力场景的 SD1.5 基础生图模型，适合稳定复现变电站、输电线路等工业画面。',
  },
  'sd15-electric-specialized': {
    display_name: 'SD 1.5 电力专精版',
    description: '在电力领域数据上微调的 SD1.5 部署模型，更擅长设备结构、布线细节与工业质感。',
  },
  'ssd1b-electric': {
    display_name: 'SSD-1B 电力极速版',
    description: '面向本地低显存生成优化的 SSD-1B 蒸馏模型，启动更轻、出图更快。',
  },
  'unipic2-kontext': {
    display_name: 'UniPic2 电力场景版',
    description: '更强调复杂语义和场景上下文的电力生成模型，适合多元素组合画面。',
  },
  'electric-score-v1': {
    display_name: '电力评分 V1（兼容版）',
    description: '兼容旧流程的四维评分模型，组合 ImageReward、CLIP-IQA 与美学预测能力。',
  },
  'electric-score-v2': {
    display_name: '电力评分 V2（电力域增强）',
    description: '面向电力场景重新训练的轻量四维评分模型，更适合 Apple GPU 和小显存环境。',
  },
  'image-reward': {
    display_name: 'ImageReward 文图对齐评分',
    description: '用于评估提示词与生成图像匹配程度的评分模型。',
  },
  'aesthetic-predictor': {
    display_name: '美学构图评分器',
    description: '用于评估画面美感、构图与整体观感的评分模型。',
  },
}

export function localizeModelRecord(model: ModelRecord): ModelRecord {
  const localizedCopy = LOCALIZED_MODEL_COPY[model.model_name]
  if (!localizedCopy) {
    return model
  }

  return {
    ...model,
    display_name: localizedCopy.display_name,
    description: localizedCopy.description,
  }
}

export function localizeModelRecords(models: ModelRecord[]): ModelRecord[] {
  return models.map(localizeModelRecord)
}

