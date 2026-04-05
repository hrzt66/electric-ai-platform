from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_generate_returns_file_path_and_scores():
    response = client.post(
        "/internal/generate",
        json={
            "job_id": 1,
            "prompt": "A wind turbine farm at sunset",
            "negative_prompt": "blurry",
            "model_name": "UniPic-2",
            "seed": 42,
            "steps": 20,
            "guidance_scale": 7.5,
        },
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["file_path"].endswith(".png")
    assert payload["scores"]["visual_fidelity"] >= 0


def test_runtime_status_returns_directory_probe():
    response = client.get("/runtime/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["runtime_root"] == r"G:\electric-ai-runtime"
    assert "directories" in payload
