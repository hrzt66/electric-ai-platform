# YOLO Superclass Rebuild Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the auxiliary YOLO detector and supporting public scene dataset so `electric-score-v2` can target `mAP50 ~= 0.7` and `mAP50-95 ~= 0.5` with a 7-class superclass taxonomy aligned to the user's prompt distribution.

**Architecture:** Split the work into four parts: public image acquisition, detection-source ingestion, superclass remapping and training-pipeline unification, and final training plus verification. Keep all outputs inside the existing `model/` runtime tree and reuse the repo's current dataset conventions.

**Tech Stack:** Python, Ultralytics YOLOv8, Hugging Face datasets, Openverse/Wikimedia download flow, local MPS training on macOS.

---

### Task 1: Extend public scene-image downloading

**Files:**
- Modify: `python-ai-service/training/generation/public_dataset.py`
- Modify: `python-ai-service/scripts/prepare_generation_v3_dataset.py`
- Test: `python-ai-service/tests/test_generation_prepare_dataset.py`

- [ ] **Step 1: Write the failing test**

Add expectations that the public bucket map includes `hydro`, `control_room`, and `night_maintenance`, and that the collection pipeline can emit rows into those buckets.

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/bin/python -m pytest python-ai-service/tests/test_generation_prepare_dataset.py -q`
Expected: FAIL because the new buckets are not yet defined.

- [ ] **Step 3: Write minimal implementation**

Extend the public bucket query configuration so new scene categories download into the existing `generation-v3/raw` tree with sidecar attribution metadata.

- [ ] **Step 4: Run test to verify it passes**

Run: `./.venv/bin/python -m pytest python-ai-service/tests/test_generation_prepare_dataset.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add python-ai-service/training/generation/public_dataset.py python-ai-service/scripts/prepare_generation_v3_dataset.py python-ai-service/tests/test_generation_prepare_dataset.py
git commit -m "feat: extend public scene dataset buckets"
```

### Task 2: Add new public detection sources and superclass mappings

**Files:**
- Modify: `python-ai-service/training/scoring/config.py`
- Modify: `python-ai-service/training/scoring/datasets.py`
- Test: `python-ai-service/tests/test_scoring_datasets.py`

- [ ] **Step 1: Write the failing test**

Add tests for source-label remapping into:
- `substation_primary`
- `transmission_tower`
- `insulator_string`
- `wind_turbine`
- `solar_panel`
- `dam`
- `maintenance_ppe`

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/bin/python -m pytest python-ai-service/tests/test_scoring_datasets.py -q`
Expected: FAIL because the current config and remapper only know the old component classes.

- [ ] **Step 3: Write minimal implementation**

Update scoring config with the new superclass list and public source definitions. Add source-specific label remapping logic and deterministic normalization for the new datasets.

- [ ] **Step 4: Run test to verify it passes**

Run: `./.venv/bin/python -m pytest python-ai-service/tests/test_scoring_datasets.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add python-ai-service/training/scoring/config.py python-ai-service/training/scoring/datasets.py python-ai-service/tests/test_scoring_datasets.py
git commit -m "feat: add scoring superclass dataset mappings"
```

### Task 3: Rebuild prompt aliasing and merge behavior

**Files:**
- Modify: `python-ai-service/training/scoring/modeling.py`
- Modify: `python-ai-service/app/runtimes/scorers/power_score_runtime.py`
- Modify: `python-ai-service/training/scoring/pipeline.py`
- Test: `python-ai-service/tests/test_scoring_yolo_merge.py`
- Test: `python-ai-service/tests/test_scoring_v2_config.py`

- [ ] **Step 1: Write the failing test**

Add tests that:
- merged YOLO dataset exports the new class list
- old component labels are remapped into superclasses
- prompt alias matching uses the new scene-aligned class schema

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/bin/python -m pytest python-ai-service/tests/test_scoring_yolo_merge.py python-ai-service/tests/test_scoring_v2_config.py -q`
Expected: FAIL because current aliases and merged names still use the old component taxonomy.

- [ ] **Step 3: Write minimal implementation**

Update alias tables, merge code, and runtime grounding logic so the downstream scoring path uses the same 7 classes as training.

- [ ] **Step 4: Run test to verify it passes**

Run: `./.venv/bin/python -m pytest python-ai-service/tests/test_scoring_yolo_merge.py python-ai-service/tests/test_scoring_v2_config.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add python-ai-service/training/scoring/modeling.py python-ai-service/app/runtimes/scorers/power_score_runtime.py python-ai-service/training/scoring/pipeline.py python-ai-service/tests/test_scoring_yolo_merge.py python-ai-service/tests/test_scoring_v2_config.py
git commit -m "feat: align scoring runtime with yolo superclasses"
```

### Task 4: Download public scene images and stage new detection data

**Files:**
- Modify: `model/datasets/generation-v3/raw/...`
- Modify: `model/datasets/scoring-v2/raw/...`
- Modify: `model/datasets/scoring-v2/manifests/...` after rebuild

- [ ] **Step 1: Download public scene images**

Run the generation public-download script with the new buckets and verify attribution sidecars are written.

- [ ] **Step 2: Download or materialize new public detection sources**

Fetch the new public labeled datasets into the scoring raw-data tree without changing global system state.

- [ ] **Step 3: Verify staging**

Confirm class names, image counts, and label availability before training.

- [ ] **Step 4: Commit**

Do not commit large binary datasets unless explicitly intended by the repo workflow. If datasets are git-ignored, commit only code or manifest changes.

### Task 5: Retrain detector and verify target metrics

**Files:**
- Modify: `model/training/scoring/electric-score-v2/...`
- Modify: `model/scoring/electric-score-v2/...`

- [ ] **Step 1: Run rebuilt training**

Run the unified training entrypoint with the new superclass configuration.

- [ ] **Step 2: Validate metrics**

Capture:
- per-class counts
- final validation metrics
- exported bundle paths

- [ ] **Step 3: Verify consistency**

Check that:
- training report and bundle metrics reference the same merged dataset
- bundled class list matches runtime aliases
- target metrics are met or the closest shortfall is explained by data support

- [ ] **Step 4: Commit**

Commit code changes and lightweight reports only if appropriate for the repo workflow.
