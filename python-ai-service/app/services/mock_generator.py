from pathlib import Path

from PIL import Image, ImageDraw

from app.services.mock_scorer import score_from_prompt


def generate_placeholder(job_id: int, prompt: str) -> dict:
    output_dir = Path("../storage/images").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"job-{job_id}.png"

    image = Image.new("RGB", (1024, 768), color=(26, 72, 124))
    draw = ImageDraw.Draw(image)
    draw.text((40, 60), prompt[:80], fill=(255, 255, 255))
    image.save(output_path)

    return {
        "file_path": str(output_path),
        "scores": score_from_prompt(prompt),
    }
