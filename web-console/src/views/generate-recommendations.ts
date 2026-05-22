export type ElectricMainClass =
  | 'substation_primary'
  | 'transmission_tower'
  | 'wind_turbine'
  | 'solar_panel'
  | 'dam'

export type GenerationPromptPreset = {
  targetClass: ElectricMainClass
  label: string
  positivePrompt: string
  negativePrompt: string
}

const SYSTEM_NEGATIVE_PROMPT =
  'cartoon, anime, illustration, CGI, low quality, blurry, heavy noise, jpeg artifacts, warped geometry, duplicated structures, floating equipment, disconnected wires, broken support structure, deformed blades, deformed tower, collapsed dam body, misaligned solar rows, gibberish text, watermark, logo'

export const ELECTRIC_SYSTEM_PROMPT_PRESETS: Record<ElectricMainClass, GenerationPromptPreset> = {
  substation_primary: {
    targetClass: 'substation_primary',
    label: '变电站',
    positivePrompt: 'electrical substation',
    negativePrompt: SYSTEM_NEGATIVE_PROMPT,
  },
  transmission_tower: {
    targetClass: 'transmission_tower',
    label: '输电塔',
    positivePrompt: 'transmission tower',
    negativePrompt: SYSTEM_NEGATIVE_PROMPT,
  },
  wind_turbine: {
    targetClass: 'wind_turbine',
    label: '风力发电机',
    positivePrompt: 'wind turbine',
    negativePrompt: SYSTEM_NEGATIVE_PROMPT,
  },
  solar_panel: {
    targetClass: 'solar_panel',
    label: '光伏板',
    positivePrompt: 'solar panel',
    negativePrompt: SYSTEM_NEGATIVE_PROMPT,
  },
  dam: {
    targetClass: 'dam',
    label: '大坝',
    positivePrompt: 'dam',
    negativePrompt: SYSTEM_NEGATIVE_PROMPT,
  },
}

const TARGET_CLASS_KEYWORDS: Array<{ targetClass: ElectricMainClass; keywords: string[] }> = [
  {
    targetClass: 'substation_primary',
    keywords: ['substation_primary', 'substation', 'switchyard', 'transformer', 'busbar', 'breaker', '变电站', '变压器', '母线'],
  },
  {
    targetClass: 'transmission_tower',
    keywords: ['transmission_tower', 'transmission tower', 'tower', 'pylon', 'power line', '输电塔', '铁塔', '杆塔', '输电线'],
  },
  {
    targetClass: 'wind_turbine',
    keywords: ['wind_turbine', 'wind turbine', 'wind farm', 'turbine', '风机', '风力发电机', '风电'],
  },
  {
    targetClass: 'solar_panel',
    keywords: ['solar_panel', 'solar panel', 'photovoltaic', 'solar farm', 'solar array', '光伏', '太阳能板', '光伏板'],
  },
  {
    targetClass: 'dam',
    keywords: ['dam', 'hydroelectric', 'hydropower', '大坝', '水坝', '水电站'],
  },
]

const SYSTEM_PROMPT_CLASS_ORDER: ElectricMainClass[] = [
  'substation_primary',
  'transmission_tower',
  'wind_turbine',
  'solar_panel',
  'dam',
]

export function detectPromptTargetClass(prompt: string): ElectricMainClass | null {
  const normalizedPrompt = prompt.trim().toLowerCase()
  if (!normalizedPrompt) {
    return null
  }

  for (const rule of TARGET_CLASS_KEYWORDS) {
    if (rule.keywords.some((keyword) => normalizedPrompt.includes(keyword.toLowerCase()))) {
      return rule.targetClass
    }
  }
  return null
}

export function getSystemPromptPreset(targetClass: ElectricMainClass): GenerationPromptPreset {
  return ELECTRIC_SYSTEM_PROMPT_PRESETS[targetClass]
}

export function pickRandomSystemPromptPreset(randomValue = Math.random()): GenerationPromptPreset {
  const normalized = Number.isFinite(randomValue) ? Math.min(Math.max(randomValue, 0), 0.999999) : Math.random()
  const index = Math.floor(normalized * SYSTEM_PROMPT_CLASS_ORDER.length)
  return ELECTRIC_SYSTEM_PROMPT_PRESETS[SYSTEM_PROMPT_CLASS_ORDER[index]]
}
