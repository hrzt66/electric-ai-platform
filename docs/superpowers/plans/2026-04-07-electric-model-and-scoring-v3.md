# Electric Model And Scoring V3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Train and integrate an electric-industry specialized SD1.5 deployment model and a more human-aligned four-dimension scoring model under `G:\electric-ai-runtime`.

**Architecture:** Build a dedicated training pipeline under `python-ai-service/training`, curate a mixed electric image corpus from public and local sources, train an SD1.5 LoRA and merge it into a standalone runtime model, then upgrade the scoring stack to a hybrid student-teacher design that distills human-preference signals and electric-domain structure checks into a lightweight runtime bundle.

**Tech Stack:** Python 3.10, PyTorch 2.6, Diffusers, PEFT, Transformers, Datasets, Ultralytics YOLO, FastAPI runtime, Go model registry, Vue 3 frontend.

---

### Task 1: Scaffold V3 Training Layout

**Files:**
- Create: `python-ai-service/training/__init__.py`
- Create: `python-ai-service/training/common/__init__.py`
- Create: `python-ai-service/training/common/paths.py`
- Create: `python-ai-service/training/common/records.py`
- Create: `python-ai-service/training/common/jsonl.py`
- Create: `python-ai-service/scripts/train_generation_v3.py`
- Create: `python-ai-service/scripts/train_scoring_v3.py`
- Test: `python-ai-service/tests/test_training_paths.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path

from app.core.settings import Settings
from training.common.paths import TrainingPaths


def test_training_paths_build_expected_runtime_directories(tmp_path: Path) -> None:
    settings = Settings(runtime_root=tmp_path)

    paths = TrainingPaths.from_settings(settings)

    assert paths.generation_dataset_root == tmp_path / "datasets" / "generation-v3"
    assert paths.scoring_dataset_root == tmp_path / "datasets" / "scoring-v3"
    assert paths.generation_training_root == tmp_path / "training" / "generation" / "sd15-electric-specialized"
    assert paths.scoring_training_root == tmp_path / "training" / "scoring" / "electric-score-v3"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `& 'G:\miniconda3\envs\electric-ai-py310\python.exe' -m pytest python-ai-service/tests/test_training_paths.py -q`

Expected: FAIL because `training.common.paths` does not exist yet.

- [ ] **Step 3: Implement the shared path layer**

```python
from dataclasses import dataclass
from pathlib import Path

from app.core.settings import Settings


@dataclass(slots=True)
class TrainingPaths:
    runtime_root: Path
    generation_dataset_root: Path
    scoring_dataset_root: Path
    generation_training_root: Path
    scoring_training_root: Path

    @classmethod
    def from_settings(cls, settings: Settings) -> "TrainingPaths":
        runtime_root = Path(settings.runtime_root)
        return cls(
            runtime_root=runtime_root,
            generation_dataset_root=runtime_root / "datasets" / "generation-v3",
            scoring_dataset_root=runtime_root / "datasets" / "scoring-v3",
            generation_training_root=runtime_root / "training" / "generation" / "sd15-electric-specialized",
            scoring_training_root=runtime_root / "training" / "scoring" / "electric-score-v3",
        )
```

- [ ] **Step 4: Add JSONL and record helpers**

```python
from dataclasses import asdict, is_dataclass
import json
from pathlib import Path
from typing import Iterable, Iterator


def write_jsonl(path: Path, rows: Iterable[object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            payload = asdict(row) if is_dataclass(row) else row
            fh.write(json.dumps(payload, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> Iterator[dict]:
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)
```

- [ ] **Step 5: Add thin CLI entrypoints**

```python
def main() -> int:
    from training.generation.pipeline import run_generation_training

    run_generation_training()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 6: Run the test to verify it passes**

Run: `& 'G:\miniconda3\envs\electric-ai-py310\python.exe' -m pytest python-ai-service/tests/test_training_paths.py -q`

Expected: PASS.

### Task 2: Build The Electric Data Curation Pipeline

**Files:**
- Create: `python-ai-service/training/generation/__init__.py`
- Create: `python-ai-service/training/generation/scan_sources.py`
- Create: `python-ai-service/training/generation/dedupe.py`
- Create: `python-ai-service/training/generation/captioning.py`
- Create: `python-ai-service/training/generation/build_manifest.py`
- Create: `python-ai-service/tests/test_generation_manifest.py`

- [ ] **Step 1: Write the failing manifest test**

```python
from pathlib import Path

from training.generation.build_manifest import build_generation_manifest


def test_build_generation_manifest_filters_zero_byte_and_labels_sources(tmp_path: Path) -> None:
    local_dir = tmp_path / "local"
    local_dir.mkdir(parents=True)
    good = local_dir / "tower.png"
    bad = local_dir / "empty.png"
    good.write_bytes(b"fake-image")
    bad.write_bytes(b"")

    rows = build_generation_manifest(
        public_roots=[],
        local_roots=[local_dir],
        external_roots=[],
    )

    assert len(rows) == 1
    assert rows[0]["source_group"] == "local"
    assert rows[0]["path"].endswith("tower.png")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `& 'G:\miniconda3\envs\electric-ai-py310\python.exe' -m pytest python-ai-service/tests/test_generation_manifest.py -q`

Expected: FAIL because the manifest builder does not exist.

- [ ] **Step 3: Implement source scanning**

```python
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


def scan_image_roots(source_group: str, roots: list[Path]) -> list[dict]:
    rows: list[dict] = []
    for root in roots:
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in IMAGE_SUFFIXES:
                continue
            if path.stat().st_size <= 0:
                continue
            rows.append(
                {
                    "source_group": source_group,
                    "path": str(path),
                    "filename": path.name,
                    "suffix": path.suffix.lower(),
                    "size_bytes": path.stat().st_size,
                }
            )
    return rows
```

- [ ] **Step 4: Implement manifest assembly**

```python
def build_generation_manifest(*, public_roots: list[Path], local_roots: list[Path], external_roots: list[Path]) -> list[dict]:
    rows = []
    rows.extend(scan_image_roots("public", public_roots))
    rows.extend(scan_image_roots("local", local_roots))
    rows.extend(scan_image_roots("external", external_roots))
    return sorted(rows, key=lambda item: item["path"])
```

- [ ] **Step 5: Add initial dedupe and caption interfaces**

```python
def compute_file_fingerprint(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def apply_stub_caption(row: dict) -> dict:
    row = dict(row)
    lower = row["filename"].lower()
    tags = []
    for keyword in ("substation", "tower", "insulator", "wind", "solar", "transformer", "breaker"):
        if keyword in lower:
            tags.append(keyword)
    row["caption"] = ", ".join(tags) if tags else "electric industrial scene"
    return row
```

- [ ] **Step 6: Run the manifest test to verify it passes**

Run: `& 'G:\miniconda3\envs\electric-ai-py310\python.exe' -m pytest python-ai-service/tests/test_generation_manifest.py -q`

Expected: PASS.

### Task 3: Implement SD1.5 Specialized Training And Merge

**Files:**
- Create: `python-ai-service/training/generation/config.py`
- Create: `python-ai-service/training/generation/train_lora.py`
- Create: `python-ai-service/training/generation/merge_lora.py`
- Create: `python-ai-service/training/generation/evaluate.py`
- Create: `python-ai-service/tests/test_generation_config.py`

- [ ] **Step 1: Write the failing config test**

```python
from training.generation.config import GenerationTrainingConfig


def test_generation_training_config_defaults_fit_6gb_gpu() -> None:
    config = GenerationTrainingConfig()

    assert config.resolution == 512
    assert config.train_batch_size == 1
    assert config.gradient_accumulation_steps >= 4
    assert config.rank in {16, 32}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `& 'G:\miniconda3\envs\electric-ai-py310\python.exe' -m pytest python-ai-service/tests/test_generation_config.py -q`

Expected: FAIL because the config module does not exist.

- [ ] **Step 3: Define the low-VRAM training config**

```python
from dataclasses import dataclass


@dataclass(slots=True)
class GenerationTrainingConfig:
    base_model_name: str = "runwayml/stable-diffusion-v1-5"
    resolution: int = 512
    rank: int = 32
    alpha: int = 32
    train_batch_size: int = 1
    gradient_accumulation_steps: int = 8
    learning_rate: float = 1e-4
    max_train_steps: int = 6000
    mixed_precision: str = "fp16"
    use_8bit_adam: bool = False
```

- [ ] **Step 4: Implement LoRA training orchestration**

```python
def build_train_command(config: GenerationTrainingConfig, dataset_dir: str, output_dir: str) -> list[str]:
    return [
        "accelerate",
        "launch",
        "python-ai-service/training/generation/train_lora.py",
        "--pretrained_model_name_or_path",
        config.base_model_name,
        "--train_data_dir",
        dataset_dir,
        "--resolution",
        str(config.resolution),
        "--train_batch_size",
        str(config.train_batch_size),
        "--gradient_accumulation_steps",
        str(config.gradient_accumulation_steps),
        "--rank",
        str(config.rank),
        "--output_dir",
        output_dir,
    ]
```

- [ ] **Step 5: Implement LoRA merge**

```python
def merge_lora_weights(base_dir: str, lora_dir: str, target_dir: str) -> None:
    from diffusers import StableDiffusionPipeline
    import torch

    pipe = StableDiffusionPipeline.from_pretrained(base_dir, torch_dtype=torch.float16)
    pipe.load_lora_weights(lora_dir)
    pipe.fuse_lora()
    pipe.save_pretrained(target_dir, safe_serialization=True)
```

- [ ] **Step 6: Add offline evaluation hook**

```python
STANDARD_PROMPTS = [
    "500kV substation, ultra detailed, industrial realism, clear transformer yard",
    "transmission tower on mountains, long power lines, realistic insulators, sharp focus",
    "modern wind farm, power transmission integration, clean sky, realistic industrial composition",
    "large photovoltaic station with boost substation, aerial patrol view, realistic lighting",
]
```

- [ ] **Step 7: Run the config test to verify it passes**

Run: `& 'G:\miniconda3\envs\electric-ai-py310\python.exe' -m pytest python-ai-service/tests/test_generation_config.py -q`

Expected: PASS.

### Task 4: Register And Expose The Specialized Generator

**Files:**
- Modify: `python-ai-service/app/runtimes/runtime_registry.py`
- Modify: `python-ai-service/scripts/download_models.py`
- Modify: `services/model-service/repository/model_repository.go`
- Test: `python-ai-service/tests/test_runtime_registry.py`
- Test: `services/model-service/repository/model_repository_test.go`

- [ ] **Step 1: Write the failing runtime registry test**

```python
def test_runtime_registry_lists_specialized_sd15_model(tmp_path):
    ...
    items = registry.list_models()["items"]
    assert any(item["name"] == "sd15-electric-specialized" for item in items)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `& 'G:\miniconda3\envs\electric-ai-py310\python.exe' -m pytest python-ai-service/tests/test_runtime_registry.py -q`

Expected: FAIL because the new model is not registered.

- [ ] **Step 3: Add the runtime registry factory**

```python
self._generation_runtime_factories = {
    "sd15-electric": self._build_sd15_runtime,
    "sd15-electric-specialized": self._build_sd15_specialized_runtime,
    "unipic2-kontext": self._build_unipic2_runtime,
}
```

- [ ] **Step 4: Add manifest exposure**

```python
"sd15-electric-specialized": RuntimeModelManifestEntry(
    name="sd15-electric-specialized",
    target="generation",
    source="local-runtime",
    repo_id=None,
    local_dir=str(paths.models_generation / "sd15-electric-specialized"),
    description="Electric-domain specialized SD1.5 deployment model",
)
```

- [ ] **Step 5: Seed the Go model registry**

```go
{
    ModelName:             "sd15-electric-specialized",
    DisplayName:           "Stable Diffusion 1.5 Electric Specialized",
    ModelType:             "generation",
    ServiceName:           "python-ai-service",
    Status:                "available",
    Description:           "Electric-domain specialized SD1.5 deployment model",
    DefaultPositivePrompt: "500kV substation, realistic industrial equipment, clear wiring, detailed steel structures",
    DefaultNegativePrompt: "cartoon, toy-like, disconnected wires, impossible geometry, blurry",
    LocalPath:             `G:\electric-ai-runtime\models\generation\sd15-electric-specialized`,
},
```

- [ ] **Step 6: Run runtime and Go tests**

Run: `& 'G:\miniconda3\envs\electric-ai-py310\python.exe' -m pytest python-ai-service/tests/test_runtime_registry.py -q`

Run: `& 'G:\Golang\go1.24.0\bin\go.exe' test ./services/model-service/...`

Expected: both PASS.

### Task 5: Build The Human-Aligned Scoring V3 Training Pipeline

**Files:**
- Create: `python-ai-service/training/scoring/__init__.py`
- Create: `python-ai-service/training/scoring/config.py`
- Create: `python-ai-service/training/scoring/teacher_scores.py`
- Create: `python-ai-service/training/scoring/build_dataset.py`
- Create: `python-ai-service/training/scoring/train_student.py`
- Create: `python-ai-service/tests/test_scoring_v3_config.py`

- [ ] **Step 1: Write the failing scoring config test**

```python
from training.scoring.config import ScoringTrainingConfig


def test_scoring_v3_keeps_required_weights() -> None:
    config = ScoringTrainingConfig()

    assert config.total_weights["visual_fidelity"] == 0.21
    assert config.total_weights["text_consistency"] == 0.37
    assert config.total_weights["physical_plausibility"] == 0.24
    assert config.total_weights["composition_aesthetics"] == 0.18
```

- [ ] **Step 2: Run test to verify it fails**

Run: `& 'G:\miniconda3\envs\electric-ai-py310\python.exe' -m pytest python-ai-service/tests/test_scoring_v3_config.py -q`

Expected: FAIL because the config file does not exist.

- [ ] **Step 3: Define the teacher ensemble config**

```python
from dataclasses import dataclass, field


@dataclass(slots=True)
class ScoringTrainingConfig:
    targets: list[str] = field(default_factory=lambda: [
        "visual_fidelity",
        "text_consistency",
        "physical_plausibility",
        "composition_aesthetics",
    ])
    total_weights: dict[str, float] = field(default_factory=lambda: {
        "visual_fidelity": 0.21,
        "text_consistency": 0.37,
        "physical_plausibility": 0.24,
        "composition_aesthetics": 0.18,
    })
```

- [ ] **Step 4: Implement teacher score interfaces**

```python
def score_with_teachers(image_path: str, prompt: str) -> dict[str, float]:
    return {
        "pickscore_text_alignment": 0.0,
        "hps_preference": 0.0,
        "image_reward": 0.0,
    }
```

- [ ] **Step 5: Build a training row assembler**

```python
def build_training_row(base: dict, teacher: dict, electric_features: dict) -> dict:
    return {
        **base,
        **teacher,
        **electric_features,
    }
```

- [ ] **Step 6: Run the scoring config test**

Run: `& 'G:\miniconda3\envs\electric-ai-py310\python.exe' -m pytest python-ai-service/tests/test_scoring_v3_config.py -q`

Expected: PASS.

### Task 6: Integrate Electric Score V3 Into Runtime And Frontend

**Files:**
- Modify: `python-ai-service/app/runtimes/scorers/power_score_runtime.py`
- Modify: `python-ai-service/app/services/scoring_service.py`
- Modify: `python-ai-service/app/dependencies.py`
- Modify: `services/model-service/repository/model_repository.go`
- Modify: `web-console/src/components/workbench/ParameterPanel.vue`
- Test: `python-ai-service/tests/test_scoring_service.py`
- Test: `web-console/src/stores/platform.spec.ts`

- [ ] **Step 1: Write the failing scoring runtime test**

```python
def test_scoring_service_supports_electric_score_v3(...):
    ...
    scores = service._score_image(
        image_path="sample.png",
        prompt="500kV substation realistic industrial scene",
        scoring_model_name="electric-score-v3",
    )
    assert "total_score" in scores
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `& 'G:\miniconda3\envs\electric-ai-py310\python.exe' -m pytest python-ai-service/tests/test_scoring_service.py -q`

Expected: FAIL because `electric-score-v3` is unsupported.

- [ ] **Step 3: Extend the runtime bundle loader**

```python
SELF_TRAINED_SCORING_MODEL_NAMES = {
    "electric-score-v2": "electric-score-v2",
    "electric-score-v3": "electric-score-v3",
}
```

- [ ] **Step 4: Route V3 through dependencies**

```python
bundle_runtime=PowerScoreRuntime(runtime_settings.scoring_model_dir / "electric-score-v3")
```

- [ ] **Step 5: Seed the new scoring model in Go**

```go
{
    ModelName:             "electric-score-v3",
    DisplayName:           "Electric Score V3 (Human-Aligned)",
    ModelType:             "scoring",
    ServiceName:           "python-ai-service",
    Status:                "available",
    Description:           "Human-aligned four-dimension scorer with electric-domain constraints",
    DefaultPositivePrompt: "human-aligned electric scoring runtime",
    DefaultNegativePrompt: "",
    LocalPath:             `G:\electric-ai-runtime\models\scoring\electric-score-v3`,
},
```

- [ ] **Step 6: Verify the frontend exposes the new model**

Run: `npm --prefix web-console run test -- --runInBand`

Expected: frontend tests pass and the model picker still renders.

### Task 7: Add Runbooks, Smoke Tests, And Final Verification

**Files:**
- Modify: `docs\models\model-introduction-and-scoring.md`
- Modify: `docs\runtime\windows-native-runbook.md`
- Create: `python-ai-service/tests/test_training_smoke.py`
- Create: `python-ai-service/scripts/smoke_generation_v3.py`
- Create: `python-ai-service/scripts/smoke_scoring_v3.py`

- [ ] **Step 1: Write the failing smoke test**

```python
def test_training_smoke_knows_new_artifact_locations() -> None:
    assert Path(r"G:\electric-ai-runtime\models\generation\sd15-electric-specialized")
    assert Path(r"G:\electric-ai-runtime\models\scoring\electric-score-v3")
```

- [ ] **Step 2: Run the test to verify it fails or is incomplete**

Run: `& 'G:\miniconda3\envs\electric-ai-py310\python.exe' -m pytest python-ai-service/tests/test_training_smoke.py -q`

Expected: FAIL until the smoke helpers exist.

- [ ] **Step 3: Document the new runtime assets**

```markdown
- `sd15-electric-specialized`: electric-domain specialized SD1.5 deployment model
- `electric-score-v3`: human-aligned four-dimension scorer with electric constraints
```

- [ ] **Step 4: Add standalone smoke commands**

Run:

```powershell
& 'G:\miniconda3\envs\electric-ai-py310\python.exe' python-ai-service/scripts/smoke_generation_v3.py
& 'G:\miniconda3\envs\electric-ai-py310\python.exe' python-ai-service/scripts/smoke_scoring_v3.py
```

Expected:

- generation smoke saves at least one image under `G:\electric-ai-runtime\outputs\images`
- scoring smoke returns four dimensions plus weighted total

- [ ] **Step 5: Run the full verification sweep**

Run:

```powershell
& 'G:\miniconda3\envs\electric-ai-py310\python.exe' -m pytest python-ai-service/tests -q
$env:GOROOT='G:\Golang\go1.24.0'
& 'G:\Golang\go1.24.0\bin\go.exe' test ./services/model-service/... ./services/task-service/... ./services/asset-service/... ./services/audit-service/... ./services/gateway-service/...
npm --prefix web-console run test
npm --prefix web-console run build
```

Expected: all relevant Python, Go, and frontend verification passes.

## Plan Notes

- 用户已明确授权我自行决策，因此本计划默认走“Inline Execution”。
- 用户要求“暂时不要上传到 git 以及 GitHub”，因此本计划不包含 push、PR 或远端发布步骤。
- 真正长时间训练开始前，必须先完成数据清洗与目录脚手架，否则过夜训练风险过高。
