export const GENERATION_RECOMMENDED_POSITIVE_PROMPTS = [
  'modern electrical substation yard, high-voltage breakers and transformers, stainless steel busbars, gravel ground, safety fencing, warning signage sharp and legible, tidy cables, cinematic depth of field',
  'aerial view of steel lattice transmission towers marching across landscape, taut conductors, wide right-of-way, realistic insulators, rolling terrain, clear sky',
  'grid control room, wall of SCADA screens, operators at desks, LED status panels, cool white lighting, cable management neat, reflective floor, photorealistic optics',
  'utility-scale wind turbines on gentle hills, aligned rows, late afternoon sun, long shadows, crisp blades, realistic nacelles, minimal haze',
  'large photovoltaic farm, endless rows of blue PV panels, tracked mounting racks, clean gravel paths, cable trays, realistic inverters, midday sun',
  'massive concrete hydroelectric dam, spillway gates, turbulent discharge water, mist, safety railings, mountain backdrop, overcast soft light',
  'linemen performing night maintenance on transmission tower, bucket truck, headlamps, portable work lights casting rim light, reflective safety vests, visible harnesses, wet asphalt after rain',
] as const

export const GENERATION_RECOMMENDED_NEGATIVE_PROMPT =
  'cartoon, CGI, illustration, painting, anime, over-saturated, over-sharpened, blurry, soft-focus, noise, grainy, jpeg artifacts, banding, chromatic aberration, halos, lens dirt, water spots, duplicate structures, warped geometry, distorted text, gibberish signage, misaligned labels, deformed faces, deformed hands, extra limbs, floating objects'

export function pickRecommendedGenerationPrompt(randomValue = Math.random()) {
  const normalized = Number.isFinite(randomValue) ? Math.min(Math.max(randomValue, 0), 0.999999) : Math.random()
  const index = Math.floor(normalized * GENERATION_RECOMMENDED_POSITIVE_PROMPTS.length)
  return GENERATION_RECOMMENDED_POSITIVE_PROMPTS[index]
}

