# YOLO High-mAP Retrain Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the YOLO auxiliary training path so the next formal run uses a stable high-mAP profile, a cleaner merged dataset variant, and traceable epoch metrics on the existing local MPS machine.

**Architecture:** Keep the current 7-class taxonomy and `yolov8n` runtime, but split the work into three bounded units: training-profile configuration, dataset-variant rebuilding, and epoch-level reporting plus run orchestration. The failed recall-first run is treated as a dead branch; the new path introduces an explicit `high_map` profile, an `mAP-first` merged dataset variant, and a short preflight run before any 100-epoch training.

**Tech Stack:** Python, pytest, Ultralytics YOLOv8, JSONL/CSV reporting, local macOS MPS execution.

---

## File Map

- Modify: `python-ai-service/training/scoring/config.py`
  - Add explicit YOLO profile controls for `high_map` training.
- Modify: `python-ai-service/training/scoring/pipeline.py`
  - Use explicit optimizer/training args, call the new dataset-variant builder, and persist run metadata.
- Modify: `python-ai-service/training/scoring/yolo_dataset_tools.py`
  - Add `mAP-first` merged dataset rebuild and source/count summaries.
- Modify: `python-ai-service/training/reporting/yolo_epoch_metrics.py`
  - Extend metrics rows to support profile-aware logging and optional per-class payload fields.
- Modify: `python-ai-service/scripts/repair_yolo_merged_dataset.py`
  - Add CLI support to build the new `high_map_v1` dataset variant.
- Modify: `python-ai-service/scripts/monitor_yolo_epoch_metrics.py`
  - Keep epoch logging stable for CSV mode and add enough run metadata to monitor preflight vs. formal runs.
- Test: `python-ai-service/tests/test_scoring_v2_config.py`
- Test: `python-ai-service/tests/test_yolo_dataset_tools.py`
- Test: `python-ai-service/tests/test_yolo_epoch_metrics.py`

### Task 1: Add an explicit high-mAP YOLO training profile

**Files:**
- Modify: `python-ai-service/training/scoring/config.py`
- Test: `python-ai-service/tests/test_scoring_v2_config.py`

- [ ] **Step 1: Write the failing test**

Add a config test asserting the new default high-mAP profile fields exist and are stable:

```python
def test_scoring_v2_exposes_high_map_yolo_profile() -> None:
    from training.scoring.config import ScoringTrainingConfig

    config = ScoringTrainingConfig()

    assert config.yolo_profile == "high_map"
    assert config.yolo_train_variant == "high_map_v1"
    assert config.yolo_optimizer == "AdamW"
    assert config.yolo_validate_each_epoch is True
    assert config.yolo_rect is False
    assert config.yolo_mosaic == 0.2
    assert config.yolo_close_mosaic == 10
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
./.venv/bin/python -m pytest python-ai-service/tests/test_scoring_v2_config.py::test_scoring_v2_exposes_high_map_yolo_profile -q
```

Expected: FAIL because `ScoringTrainingConfig` does not yet expose the new YOLO profile fields.

- [ ] **Step 3: Write minimal implementation**

Add the new profile fields in `ScoringTrainingConfig` and surface them through `bundle_payload()` only where runtime-safe:

```python
    yolo_profile: str = "high_map"
    yolo_train_variant: str = "high_map_v1"
    yolo_optimizer: str = "AdamW"
    yolo_learning_rate: float = 3e-4
    yolo_weight_decay: float = 5e-4
    yolo_warmup_epochs: float = 1.0
    yolo_validate_each_epoch: bool = True
    yolo_rect: bool = False
    yolo_mosaic: float = 0.2
    yolo_close_mosaic: int = 10
```

Keep existing runtime-facing values untouched unless they are needed by the YOLO report.

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
./.venv/bin/python -m pytest python-ai-service/tests/test_scoring_v2_config.py -q
```

Expected: PASS, with the existing config tests still green.

- [ ] **Step 5: Commit**

```bash
git add python-ai-service/training/scoring/config.py python-ai-service/tests/test_scoring_v2_config.py
git commit -m "feat: add explicit high-map yolo profile"
```

### Task 2: Build the `mAP-first` merged dataset variant

**Files:**
- Modify: `python-ai-service/training/scoring/yolo_dataset_tools.py`
- Modify: `python-ai-service/scripts/repair_yolo_merged_dataset.py`
- Test: `python-ai-service/tests/test_yolo_dataset_tools.py`

- [ ] **Step 1: Write the failing test**

Add a dataset-tools test that creates an imbalanced merged dataset and verifies the new variant builder:

```python
def test_build_high_map_variant_rebalances_without_extreme_repeats(tmp_path: Path) -> None:
    from training.scoring.yolo_dataset_tools import build_high_map_variant

    report = build_high_map_variant(
        merged_root=tmp_path / "yolo-merged",
        variant_root=tmp_path / "yolo-merged-high-map-v1",
        max_repeat_by_class={"maintenance_ppe": 3, "solar_panel": 3, "dam": 2},
        min_box_area=0.0004,
    )

    assert report["variant_name"] == "high_map_v1"
    assert report["train_image_count"] >= report["original_train_image_count"]
    assert report["repeat_factors"]["maintenance_ppe"] <= 3
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
./.venv/bin/python -m pytest python-ai-service/tests/test_yolo_dataset_tools.py::test_build_high_map_variant_rebalances_without_extreme_repeats -q
```

Expected: FAIL because no `build_high_map_variant()` helper exists yet.

- [ ] **Step 3: Write minimal implementation**

Add a helper that copies the cleaned merged dataset into a new variant root, applies bounded class repeats on `train` only, and writes a summary JSON:

```python
def build_high_map_variant(
    *,
    merged_root: Path,
    variant_root: Path,
    max_repeat_by_class: dict[str, int],
    min_box_area: float,
) -> dict[str, object]:
    clean_yolo_dataset(merged_root)
    # copy val/test as-is
    # rebuild train with bounded repeats only
    # write high_map_variant_summary.json
    return report
```

Update `repair_yolo_merged_dataset.py` so it can run:

```bash
./.venv/bin/python python-ai-service/scripts/repair_yolo_merged_dataset.py --variant high_map_v1
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
./.venv/bin/python -m pytest python-ai-service/tests/test_yolo_dataset_tools.py -q
```

Expected: PASS, including the existing cleaning and summary tests.

- [ ] **Step 5: Commit**

```bash
git add python-ai-service/training/scoring/yolo_dataset_tools.py python-ai-service/scripts/repair_yolo_merged_dataset.py python-ai-service/tests/test_yolo_dataset_tools.py
git commit -m "feat: add high-map merged dataset variant"
```

### Task 3: Switch the pipeline to explicit high-mAP training args

**Files:**
- Modify: `python-ai-service/training/scoring/pipeline.py`
- Modify: `python-ai-service/tests/test_scoring_v2_config.py`

- [ ] **Step 1: Write the failing test**

Extend the existing YOLO training test so it asserts the formal train call no longer uses the old local-friendly profile:

```python
def test_scoring_v2_yolo_training_uses_explicit_high_map_profile(monkeypatch, tmp_path: Path) -> None:
    ...
    assert train_kwargs["optimizer"] == "AdamW"
    assert train_kwargs["lr0"] == 3e-4
    assert train_kwargs["val"] is True
    assert train_kwargs["rect"] is False
    assert train_kwargs["mosaic"] == 0.2
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
./.venv/bin/python -m pytest python-ai-service/tests/test_scoring_v2_config.py::test_scoring_v2_yolo_training_uses_explicit_high_map_profile -q
```

Expected: FAIL because `_train_yolo_auxiliary()` still uses `optimizer=auto`, `rect=True`, and the old validation flow.

- [ ] **Step 3: Write minimal implementation**

Update `_train_yolo_auxiliary()` so it:

- selects the new `high_map_v1` dataset variant
- passes explicit YOLO optimizer and schedule args
- saves the exact dataset path and profile name in the report

Use a train call shaped like:

```python
train_result = model.train(
    data=str(primary_yaml),
    epochs=config.yolo_epochs,
    imgsz=config.yolo_image_size,
    batch=config.yolo_batch_size,
    optimizer=config.yolo_optimizer,
    lr0=config.yolo_learning_rate,
    weight_decay=config.yolo_weight_decay,
    warmup_epochs=config.yolo_warmup_epochs,
    val=config.yolo_validate_each_epoch,
    rect=config.yolo_rect,
    mosaic=config.yolo_mosaic,
    close_mosaic=config.yolo_close_mosaic,
    plots=False,
)
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
./.venv/bin/python -m pytest python-ai-service/tests/test_scoring_v2_config.py -q
```

Expected: PASS, including the pipeline training test.

- [ ] **Step 5: Commit**

```bash
git add python-ai-service/training/scoring/pipeline.py python-ai-service/tests/test_scoring_v2_config.py
git commit -m "feat: use explicit high-map yolo training profile"
```

### Task 4: Make epoch monitoring durable enough for preflight and formal runs

**Files:**
- Modify: `python-ai-service/training/reporting/yolo_epoch_metrics.py`
- Modify: `python-ai-service/scripts/monitor_yolo_epoch_metrics.py`
- Test: `python-ai-service/tests/test_yolo_epoch_metrics.py`

- [ ] **Step 1: Write the failing test**

Add a monitor/reporting test for profile-aware JSONL rows:

```python
def test_build_metrics_record_from_results_row_keeps_core_map_fields() -> None:
    from training.reporting.yolo_epoch_metrics import build_metrics_record_from_results_row

    record = build_metrics_record_from_results_row(
        row={...},
        weights_path=Path("/tmp/last.pt"),
        extra={"profile": "high_map", "dataset_variant": "high_map_v1"},
    )

    assert record.status == "ok"
```

If the dataclass remains fixed-width, store the extra fields in the emitted dict returned by a new helper instead of on the dataclass itself.

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
./.venv/bin/python -m pytest python-ai-service/tests/test_yolo_epoch_metrics.py -q
```

Expected: FAIL because no profile-aware record builder exists yet.

- [ ] **Step 3: Write minimal implementation**

Keep the current dataclass stable for backward compatibility, but add a helper that returns an appendable payload with run metadata:

```python
def build_metrics_payload(*, record: YoloEpochMetricsRecord, extra: Mapping[str, object] | None = None) -> dict[str, object]:
    payload = asdict(record)
    if extra:
        payload.update(extra)
    return payload
```

Use that helper in `monitor_yolo_epoch_metrics.py` so preflight and formal runs can be distinguished in `yolo_epoch_metrics.jsonl`.

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
./.venv/bin/python -m pytest python-ai-service/tests/test_yolo_epoch_metrics.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add python-ai-service/training/reporting/yolo_epoch_metrics.py python-ai-service/scripts/monitor_yolo_epoch_metrics.py python-ai-service/tests/test_yolo_epoch_metrics.py
git commit -m "feat: add profile-aware yolo epoch reporting"
```

### Task 5: Verify the code path and launch the new preflight run

**Files:**
- Modify: `model/training/scoring/electric-score-v2/...` run outputs only

- [ ] **Step 1: Run the targeted automated test suite**

Run:

```bash
./.venv/bin/python -m pytest python-ai-service/tests/test_yolo_dataset_tools.py python-ai-service/tests/test_yolo_epoch_metrics.py python-ai-service/tests/test_scoring_v2_config.py python-ai-service/tests/test_scoring_yolo_merge.py -q
```

Expected: PASS.

- [ ] **Step 2: Rebuild the high-mAP dataset variant**

Run:

```bash
./.venv/bin/python python-ai-service/scripts/repair_yolo_merged_dataset.py --variant high_map_v1
```

Expected: a new `high_map_v1` variant summary under `model/training/scoring/electric-score-v2/`.

- [ ] **Step 3: Launch the 5-epoch high-mAP preflight**

Run:

```bash
HF_HOME='model/hf-home' \
ELECTRIC_AI_RUNTIME_ROOT='model' \
PYTHONPATH='python-ai-service' \
./.venv/bin/python python-ai-service/scripts/train_scoring_v2.py \
  --device mps \
  --yolo-epochs 5 \
  --yolo-imgsz 512 \
  --yolo-batch-size 8
```

Expected: a new YOLO run directory and epoch metrics written each epoch.

- [ ] **Step 4: Evaluate go/no-go for the 100-epoch formal run**

Use the recorded metrics to enforce:

- no repeated `mAP50` collapse after epoch 1
- recall materially above the failed run's `~0.10`
- validation losses not degrading monotonically

If these checks pass, start the 100-epoch formal run with the same high-mAP profile. If they fail, stop and revise the profile before any long run.

- [ ] **Step 5: Commit**

Do not commit large generated training artifacts. Commit only code and lightweight plan/spec/test updates if a code checkpoint is needed:

```bash
git add docs/superpowers/specs/2026-04-24-yolo-high-map-retrain-design.md docs/superpowers/plans/2026-04-24-yolo-high-map-retrain.md python-ai-service/training/scoring/config.py python-ai-service/training/scoring/pipeline.py python-ai-service/training/scoring/yolo_dataset_tools.py python-ai-service/training/reporting/yolo_epoch_metrics.py python-ai-service/scripts/repair_yolo_merged_dataset.py python-ai-service/scripts/monitor_yolo_epoch_metrics.py python-ai-service/tests/test_scoring_v2_config.py python-ai-service/tests/test_yolo_dataset_tools.py python-ai-service/tests/test_yolo_epoch_metrics.py
git commit -m "feat: add high-map yolo retrain pipeline"
```
