from fastapi import FastAPI

from app.schemas.jobs import GenerateRequest
from app.services.mock_generator import generate_placeholder
from scripts.download_models import get_model_manifest
from scripts.runtime_probe import build_runtime_probe

app = FastAPI(title="python-ai-service")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/runtime/status")
def runtime_status() -> dict:
    return build_runtime_probe()


@app.get("/runtime/models")
def runtime_models() -> dict:
    return {"items": list(get_model_manifest().values())}


@app.post("/internal/generate")
def generate(request: GenerateRequest) -> dict:
    result = generate_placeholder(request.job_id, request.prompt)
    return {"code": 0, "message": "success", "data": result, "trace_id": f"job-{request.job_id}"}
