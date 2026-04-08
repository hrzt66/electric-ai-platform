# Electric Specialized SD1.5 Evaluation And Deployment Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Verify the finished electric specialized SD1.5 model with a fresh manual evaluation run, perform a real generation test, and confirm the model is deployed into the project runtime path and registry flow.

**Architecture:** Reuse the trained model already merged into `G:\electric-ai-runtime\models\generation\sd15-electric-specialized`, run the same evaluation pipeline manually against that deployed model, then exercise the project's generation runtime with the specialized model name. Deployment verification is done by checking the project runtime registry and model catalog wiring rather than retraining or re-merging.

**Tech Stack:** Python 3.10 runtime, Diffusers Stable Diffusion pipeline, project `SD15Runtime`, PowerShell, Go model registry wiring

---

### Task 1: Confirm Final Training Artifacts

**Files:**
- Read: `G:\electric-ai-runtime\training\generation\sd15-electric-specialized\session-logs\monitor-status.json`
- Read: `G:\electric-ai-runtime\models\generation\sd15-electric-specialized`
- Read: `G:\electric-ai-runtime\training\generation\sd15-electric-specialized\evaluation`

- [ ] **Step 1: Read monitor status and artifact directories**

Run: `Get-Content G:\electric-ai-runtime\training\generation\sd15-electric-specialized\session-logs\monitor-status.json`
Expected: status is `completed` and points at the specialized model directory.

- [ ] **Step 2: Verify merged model files exist**

Run: `Get-ChildItem G:\electric-ai-runtime\models\generation\sd15-electric-specialized -Force`
Expected: `model_index.json` plus diffusion component directories such as `unet`, `vae`, `scheduler`, `tokenizer`, and `text_encoder`.

- [ ] **Step 3: Verify evaluation outputs exist before rerun**

Run: `Get-ChildItem G:\electric-ai-runtime\training\generation\sd15-electric-specialized\evaluation -Force`
Expected: prior `evaluation_report.json` and validation images are present.

### Task 2: Run A Fresh Manual Evaluation

**Files:**
- Read/Write: `G:\electric-ai-runtime\training\generation\sd15-electric-specialized\evaluation\evaluation_report.json`
- Read/Write: `G:\electric-ai-runtime\training\generation\sd15-electric-specialized\evaluation\validation_00.png`
- Read/Write: `G:\electric-ai-runtime\training\generation\sd15-electric-specialized\evaluation\validation_01.png`
- Read/Write: `G:\electric-ai-runtime\training\generation\sd15-electric-specialized\evaluation\validation_02.png`
- Read/Write: `G:\electric-ai-runtime\training\generation\sd15-electric-specialized\evaluation\validation_03.png`
- Read: `E:\毕业设计\golang-毕业设计\.worktrees\electric-score-v2\python-ai-service\training\generation\evaluate.py`

- [ ] **Step 1: Manually execute the evaluation entrypoint against the deployed specialized model**

Run:

```powershell
$env:PYTHONPATH='E:\毕业设计\golang-毕业设计\.worktrees\electric-score-v2\python-ai-service'
@'
import json
from pathlib import Path

from training.generation.config import GenerationTrainingConfig
from training.generation.evaluate import evaluate_generation_model

report = evaluate_generation_model(
    model_dir=Path(r"G:\electric-ai-runtime\models\generation\sd15-electric-specialized"),
    output_dir=Path(r"G:\electric-ai-runtime\training\generation\sd15-electric-specialized\evaluation"),
    config=GenerationTrainingConfig(),
)
print(json.dumps(report, ensure_ascii=False, indent=2))
'@ | & 'G:\miniconda3\envs\electric-ai-py310\python.exe' -
```

Expected: exit code `0`, refreshed `evaluation_report.json`, and four validation images regenerated.

- [ ] **Step 2: Verify the new evaluation report timestamp**

Run: `Get-ChildItem G:\electric-ai-runtime\training\generation\sd15-electric-specialized\evaluation -Force | Sort-Object LastWriteTime -Descending`
Expected: `evaluation_report.json` and validation images have fresh timestamps from this manual run.

### Task 3: Perform A Real Generation Test

**Files:**
- Read: `E:\毕业设计\golang-毕业设计\.worktrees\electric-score-v2\python-ai-service\app\runtimes\sd15_runtime.py`
- Write: `G:\electric-ai-runtime\outputs\images\*`

- [ ] **Step 1: Execute one real generation through the project runtime**

Run:

```powershell
$env:PYTHONPATH='E:\毕业设计\golang-毕业设计\.worktrees\electric-score-v2\python-ai-service'
@'
import json
from pathlib import Path

from app.runtimes.sd15_runtime import SD15Runtime

runtime = SD15Runtime(
    model_dir=Path(r"G:\electric-ai-runtime\models\generation\sd15-electric-specialized"),
    output_dir=Path(r"G:\electric-ai-runtime\outputs\images"),
)
images = runtime.generate(
    job_id=9001,
    prompt="500kV substation, ultra realistic industrial documentary photography, detailed transformer yard, insulators, gantries, clear wiring",
    negative_prompt="cartoon, blurry, disconnected wires, toy-like, impossible geometry",
    seed=42,
    width=512,
    height=512,
    steps=24,
    guidance_scale=7.0,
    num_images=1,
    model_name="sd15-electric-specialized",
)
print(json.dumps(images, ensure_ascii=False, indent=2))
runtime.unload()
'@ | & 'G:\miniconda3\envs\electric-ai-py310\python.exe' -
```

Expected: exit code `0` and one generated image record with a concrete file path under `G:\electric-ai-runtime\outputs\images`.

- [ ] **Step 2: Verify the generated image file exists**

Run: `Get-ChildItem G:\electric-ai-runtime\outputs\images -File | Sort-Object LastWriteTime -Descending | Select-Object -First 5`
Expected: a fresh image created by the specialized model test.

### Task 4: Confirm Project Deployment Wiring

**Files:**
- Read: `E:\毕业设计\golang-毕业设计\.worktrees\electric-score-v2\python-ai-service\app\runtimes\runtime_registry.py`
- Read: `E:\毕业设计\golang-毕业设计\.worktrees\electric-score-v2\services\model-service\repository\model_repository.go`

- [ ] **Step 1: Verify python runtime registry exposes the specialized model**

Run:

```powershell
Get-Content E:\毕业设计\golang-毕业设计\.worktrees\electric-score-v2\python-ai-service\app\runtimes\runtime_registry.py
```

Expected: `sd15-electric-specialized` is present in the generation runtime factories and points to `G:\electric-ai-runtime\models\generation\sd15-electric-specialized`.

- [ ] **Step 2: Verify model-service catalog includes the specialized model**

Run:

```powershell
Get-Content E:\毕业设计\golang-毕业设计\.worktrees\electric-score-v2\services\model-service\repository\model_repository.go
```

Expected: seeded catalog entry named `sd15-electric-specialized` with `available` status and the same local path.

- [ ] **Step 3: Summarize deploy status with evidence**

Evidence required:
- fresh manual evaluation output
- fresh real generation output
- runtime registry wiring
- model-service catalog wiring

