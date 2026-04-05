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


class GenerateJob(GenerateRequest):
    width: int = 512
    height: int = 512
    num_images: int = 1


class TaskStatusUpdate(BaseModel):
    status: str
    stage: str
    error_message: str | None = None


class ScoreBundle(BaseModel):
    visual_fidelity: float
    text_consistency: float
    physical_plausibility: float
    composition_aesthetics: float
    total_score: float


class GeneratedAsset(BaseModel):
    file_path: str
    scores: ScoreBundle | None = None
