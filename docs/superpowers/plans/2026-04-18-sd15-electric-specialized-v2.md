# SD15 Electric Specialized V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a self-sufficient SD1.5 electric-domain training pipeline that downloads public electric imagery, curates a licensed dataset, trains a 100-epoch LoRA on Apple Silicon-safe settings, merges the best checkpoint into `sd15-electric-specialized`, deletes obsolete specialized artifacts, and verifies the model through the existing platform.

**Architecture:** Extend the existing generation-v3 dataset preparation stage with official public image providers and attribution manifests, then extend the SD1.5 LoRA pipeline so it can run by epochs rather than only fixed steps. Keep the platform-facing model name `sd15-electric-specialized`, but move the new training workspace to a `-v2` path and publish the merged model back into the existing deployment path.

**Tech Stack:** Python 3.13, requests/httpx, Pillow, diffusers SD1.5 LoRA example script, PyTorch MPS, existing repo training pipeline and runtime registry.

---

### Task 1: Add Public Electric Dataset Ingestion

**Files:**
- Create: `python-ai-service/training/generation/public_dataset.py`
- Modify: `python-ai-service/training/generation/prepare_dataset.py`
- Modify: `python-ai-service/scripts/prepare_generation_v3_dataset.py`
- Test: `python-ai-service/tests/test_generation_prepare_dataset.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_prepare_generation_dataset_can_download_public_provider_rows(tmp_path, monkeypatch):
    from app.core.settings import Settings
    from training.generation.prepare_dataset import prepare_generation_dataset

    downloaded = tmp_path / "downloads"
    downloaded.mkdir(parents=True)
    image_path = downloaded / "substation.png"
    image_path.write_bytes(b"img-public-electric")

    def fake_collect_public_dataset(**kwargs):
        return {
            "downloaded_rows": [
                {
                    "source_group": "public",
                    "provider": "openverse",
                    "path": str(image_path),
                    "filename": "substation.png",
                    "suffix": ".png",
                    "size_bytes": image_path.stat().st_size,
                    "caption": "realistic utility inspection photography, electric power substation",
                    "license": "cc-by",
                    "source_url": "https://example.com/substation",
                    "author": "example-author",
                }
            ],
            "attribution_rows": [
                {
                    "provider": "openverse",
                    "license": "cc-by",
                    "source_url": "https://example.com/substation",
                }
            ],
        }

    monkeypatch.setattr(
        "training.generation.prepare_dataset.collect_public_generation_dataset",
        fake_collect_public_dataset,
    )

    settings = Settings(runtime_root=tmp_path / "runtime")
    report = prepare_generation_dataset(
        settings=settings,
        public_roots=[],
        local_roots=[],
        external_roots=[],
        include_public_downloads=True,
    )

    assert report["count"] == 1
    assert Path(report["attribution_manifest_path"]).exists()
```

- [ ] **Step 2: Run the focused test to verify it fails**

Run: `./.venv/bin/python -m pytest python-ai-service/tests/test_generation_prepare_dataset.py -q`
Expected: FAIL because `include_public_downloads` and `collect_public_generation_dataset` do not exist yet.

- [ ] **Step 3: Implement public provider collection**

```python
def collect_public_generation_dataset(*, output_root: Path, provider_limits: dict[str, int] | None = None) -> dict[str, list[dict]]:
    output_root.mkdir(parents=True, exist_ok=True)
    openverse_rows, openverse_attr = _collect_openverse_rows(output_root / "openverse", limit=provider_limits.get("openverse", 0))
    wikimedia_rows, wikimedia_attr = _collect_wikimedia_rows(output_root / "wikimedia", limit=provider_limits.get("wikimedia", 0))
    return {
        "downloaded_rows": [*openverse_rows, *wikimedia_rows],
        "attribution_rows": [*openverse_attr, *wikimedia_attr],
    }
```

- [ ] **Step 4: Wire dataset preparation to write attribution manifest**

```python
if include_public_downloads:
    public_report = collect_public_generation_dataset(output_root=paths.generation_dataset_root / "raw")
    downloaded_rows = public_report["downloaded_rows"]
    attribution_rows = public_report["attribution_rows"]
else:
    downloaded_rows = []
    attribution_rows = []

manifest_rows = build_generation_manifest(
    public_roots=[*public_roots, paths.generation_dataset_root / "raw"],
    local_roots=local_roots or [],
    external_roots=external_roots or [],
    precomputed_rows=downloaded_rows,
)
write_jsonl(attribution_manifest_path, attribution_rows)
```

- [ ] **Step 5: Re-run the focused tests**

Run: `./.venv/bin/python -m pytest python-ai-service/tests/test_generation_prepare_dataset.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add python-ai-service/training/generation/public_dataset.py \
  python-ai-service/training/generation/prepare_dataset.py \
  python-ai-service/scripts/prepare_generation_v3_dataset.py \
  python-ai-service/tests/test_generation_prepare_dataset.py
git commit -m "feat: add public electric dataset ingestion"
```

### Task 2: Add Provider Filtering, Captions, and Training Paths for V2

**Files:**
- Modify: `python-ai-service/training/generation/build_manifest.py`
- Modify: `python-ai-service/training/generation/captioning.py`
- Modify: `python-ai-service/training/common/paths.py`
- Modify: `python-ai-service/training/generation/config.py`
- Test: `python-ai-service/tests/test_generation_config.py`
- Test: `python-ai-service/tests/test_training_paths.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_training_paths_use_v2_workspace_and_existing_deploy_name(tmp_path):
    from app.core.settings import Settings
    from training.common.paths import TrainingPaths
    from training.generation.config import GenerationTrainingConfig

    settings = Settings(runtime_root=tmp_path)
    paths = TrainingPaths.from_settings(settings)
    config = GenerationTrainingConfig()

    assert paths.generation_training_root == tmp_path / "training" / "generation" / "sd15-electric-specialized-v2"
    assert config.output_model_name == "sd15-electric-specialized"
    assert config.num_train_epochs == 100
```

- [ ] **Step 2: Run the focused tests to verify they fail**

Run: `./.venv/bin/python -m pytest python-ai-service/tests/test_training_paths.py python-ai-service/tests/test_generation_config.py -q`
Expected: FAIL because the current path and config still target the old workspace and no epoch field exists.

- [ ] **Step 3: Implement v2 workspace pathing and stronger caption normalization**

```python
generation_training_root=runtime_root / "training" / "generation" / "sd15-electric-specialized-v2"

@dataclass(slots=True)
class GenerationTrainingConfig:
    output_model_name: str = "sd15-electric-specialized"
    num_train_epochs: int = 100
    max_train_steps: int | None = None
    mixed_precision: str = "no"
```

- [ ] **Step 4: Ensure captions prepend the realistic electric photography prior**

```python
caption_parts = ["realistic utility inspection photography"]
_append_matching_phrases(PRIMARY_PHRASES, tokens, caption_parts)
_append_matching_phrases(DETAIL_PHRASES, tokens, caption_parts)
_append_matching_phrases(STYLE_PHRASES, tokens, caption_parts)
```

- [ ] **Step 5: Re-run the focused tests**

Run: `./.venv/bin/python -m pytest python-ai-service/tests/test_training_paths.py python-ai-service/tests/test_generation_config.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add python-ai-service/training/generation/build_manifest.py \
  python-ai-service/training/generation/captioning.py \
  python-ai-service/training/common/paths.py \
  python-ai-service/training/generation/config.py \
  python-ai-service/tests/test_generation_config.py \
  python-ai-service/tests/test_training_paths.py
git commit -m "feat: switch specialized training to v2 workspace"
```

### Task 3: Support 100-Epoch MPS-Safe LoRA Training and Best Checkpoint Selection

**Files:**
- Modify: `python-ai-service/training/generation/train_lora.py`
- Modify: `python-ai-service/training/generation/pipeline.py`
- Modify: `python-ai-service/scripts/train_generation_v3.py`
- Test: `python-ai-service/tests/test_generation_pipeline.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_prepare_generation_training_workspace_builds_epoch_based_command(tmp_path):
    from app.core.settings import Settings
    from training.generation.config import GenerationTrainingConfig
    from training.generation.pipeline import prepare_generation_training_workspace

    runtime_root = tmp_path / "runtime"
    settings = Settings(runtime_root=runtime_root)
    (runtime_root / "datasets" / "generation-v3" / "manifests").mkdir(parents=True)
    (runtime_root / "datasets" / "generation-v3" / "manifests" / "raw_manifest.jsonl").write_text("", encoding="utf-8")

    script_path = tmp_path / "train_text_to_image_lora.py"
    script_path.write_text("# stub", encoding="utf-8")

    report = prepare_generation_training_workspace(
        settings=settings,
        config=GenerationTrainingConfig(num_train_epochs=100),
        python_executable="python",
        download_script_fn=lambda _: script_path,
    )

    assert "--num_train_epochs" in report["train_command"]
    assert "100" in report["train_command"]
    assert "--max_train_steps" not in report["train_command"]
```

- [ ] **Step 2: Run the focused tests to verify they fail**

Run: `./.venv/bin/python -m pytest python-ai-service/tests/test_generation_pipeline.py -q`
Expected: FAIL because commands are still step-based only.

- [ ] **Step 3: Implement epoch-based command building and MPS-safe env**

```python
if config.max_train_steps is not None:
    command.extend(["--max_train_steps", str(config.max_train_steps)])
else:
    command.extend(["--num_train_epochs", str(config.num_train_epochs)])

env.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")
env.setdefault("ACCELERATE_USE_MPS_DEVICE", "true")
```

- [ ] **Step 4: Persist best-checkpoint metadata in the training workspace**

```python
best_checkpoint_path = select_best_generation_checkpoint(
    lora_output_dir=Path(report["lora_output_dir"]),
    evaluation_dir=Path(report["evaluation_dir"]),
)
report["best_lora_checkpoint_dir"] = str(best_checkpoint_path)
```

- [ ] **Step 5: Re-run the focused tests**

Run: `./.venv/bin/python -m pytest python-ai-service/tests/test_generation_pipeline.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add python-ai-service/training/generation/train_lora.py \
  python-ai-service/training/generation/pipeline.py \
  python-ai-service/scripts/train_generation_v3.py \
  python-ai-service/tests/test_generation_pipeline.py
git commit -m "feat: support epoch-based specialized SD15 training"
```

### Task 4: Delete Old Specialized Artifacts Before Publishing New Model

**Files:**
- Modify: `python-ai-service/training/generation/pipeline.py`
- Modify: `python-ai-service/scripts/train_generation_v3.py`
- Test: `python-ai-service/tests/test_generation_pipeline.py`

- [ ] **Step 1: Write the failing test**

```python
def test_run_generation_training_cleans_old_specialized_artifacts_before_merge(tmp_path, monkeypatch):
    from pathlib import Path
    from app.core.settings import Settings
    from training.generation.config import GenerationTrainingConfig
    from training.generation.pipeline import remove_obsolete_specialized_artifacts

    settings = Settings(runtime_root=tmp_path / "runtime")
    old_train = settings.runtime_root / "training" / "generation" / "sd15-electric-specialized"
    old_model = settings.runtime_root / "generation" / "sd15-electric-specialized"
    old_train.mkdir(parents=True)
    old_model.mkdir(parents=True)

    report = remove_obsolete_specialized_artifacts(settings)

    assert report["removed_paths"] == [str(old_train), str(old_model)]
    assert not old_train.exists()
    assert not old_model.exists()
```

- [ ] **Step 2: Run the focused tests to verify they fail**

Run: `./.venv/bin/python -m pytest python-ai-service/tests/test_generation_pipeline.py -q`
Expected: FAIL because cleanup helper does not exist yet.

- [ ] **Step 3: Implement cleanup before training/merge**

```python
def remove_obsolete_specialized_artifacts(settings: Settings) -> dict[str, object]:
    targets = [
        settings.runtime_root / "training" / "generation" / "sd15-electric-specialized",
        settings.generation_model_dir / "sd15-electric-specialized",
    ]
    removed = []
    for target in targets:
        if target.exists():
            shutil.rmtree(target)
            removed.append(str(target))
    return {"removed_paths": removed}
```

- [ ] **Step 4: Re-run the focused tests**

Run: `./.venv/bin/python -m pytest python-ai-service/tests/test_generation_pipeline.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add python-ai-service/training/generation/pipeline.py \
  python-ai-service/scripts/train_generation_v3.py \
  python-ai-service/tests/test_generation_pipeline.py
git commit -m "feat: replace old specialized model artifacts before publish"
```

### Task 5: End-to-End Verification and Training Launch

**Files:**
- Read/Write: `model/datasets/generation-v3/...`
- Read/Write: `model/training/generation/sd15-electric-specialized-v2/...`
- Read/Write: `model/generation/sd15-electric-specialized/...`

- [ ] **Step 1: Run the Python tests covering dataset prep and training pipeline**

Run: `./.venv/bin/python -m pytest python-ai-service/tests/test_generation_prepare_dataset.py python-ai-service/tests/test_generation_pipeline.py python-ai-service/tests/test_training_paths.py python-ai-service/tests/test_generation_config.py -q`
Expected: PASS.

- [ ] **Step 2: Prepare or refresh the electric public dataset**

Run: `HF_HOME=model/hf-home ELECTRIC_AI_RUNTIME_ROOT=model PYTHONPATH=python-ai-service ./.venv/bin/python python-ai-service/scripts/prepare_generation_v3_dataset.py`
Expected: JSON output containing `manifest_path`, `count`, and attribution metadata.

- [ ] **Step 3: Start the 100-epoch specialized SD1.5 training run**

Run:

```bash
HF_HOME=model/hf-home \
ELECTRIC_AI_RUNTIME_ROOT=model \
PYTHONPATH=python-ai-service \
PYTORCH_ENABLE_MPS_FALLBACK=1 \
./.venv/bin/python python-ai-service/scripts/train_generation_v3.py
```

Expected: training workspace created under `model/training/generation/sd15-electric-specialized-v2`, LoRA checkpoints written, and final merged model published to `model/generation/sd15-electric-specialized`.

- [ ] **Step 4: Verify merged model directory exists**

Run: `find model/generation/sd15-electric-specialized -maxdepth 2 -type f | sed -n '1,60p'`
Expected: SD1.5 model files are present.

- [ ] **Step 5: Exercise a real generation task through the platform**

Run:

```bash
python3 - <<'PY'
import json, time, urllib.request
base = 'http://127.0.0.1:8080/api/v1'
headers = {'Authorization': 'Bearer dev-token', 'Content-Type': 'application/json'}
payload = {
    'prompt': 'realistic electric power substation, transformer yard, daylight, industrial inspection photography',
    'negative_prompt': 'cartoon, anime, blurry, watermark',
    'model_name': 'sd15-electric-specialized',
    'scoring_model_name': 'electric-score-v2',
    'seed': 1714021800,
    'steps': 20,
    'guidance_scale': 7.5,
    'width': 512,
    'height': 512,
    'num_images': 1,
}
req = urllib.request.Request(base + '/tasks/generate', data=json.dumps(payload).encode(), headers=headers, method='POST')
job_id = json.load(urllib.request.urlopen(req))['data']['id']
print(job_id)
PY
```

Expected: a completed task with a non-black image saved in `model/image`.

- [ ] **Step 6: Commit**

```bash
git add python-ai-service scripts services web-console
git commit -m "feat: add self-bootstrapping electric SD15 training pipeline"
```
