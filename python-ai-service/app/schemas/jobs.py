from pydantic import BaseModel, ConfigDict


class GenerateRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    job_id: int
    prompt: str
    negative_prompt: str
    model_name: str
    seed: int
    steps: int
    guidance_scale: float


class ScoreBundle(BaseModel):
    visual_fidelity: float
    text_consistency: float
    physical_plausibility: float
    composition_aesthetics: float
    total_score: float
