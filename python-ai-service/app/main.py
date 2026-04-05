from fastapi import FastAPI

from app.schemas.jobs import GenerateRequest
from app.services.mock_generator import generate_placeholder

app = FastAPI(title="python-ai-service")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/internal/generate")
def generate(request: GenerateRequest) -> dict:
    result = generate_placeholder(request.job_id, request.prompt)
    return {"code": 0, "message": "success", "data": result, "trace_id": f"job-{request.job_id}"}
