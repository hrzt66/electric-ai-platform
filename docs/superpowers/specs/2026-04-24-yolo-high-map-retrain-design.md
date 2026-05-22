# YOLO High-mAP Retrain Design

## Goal

Rebuild the `electric-score-v2` auxiliary YOLO training flow so the next formal run optimizes for high validation `mAP50` and `mAP50-95`, not for recall-first experimentation, while remaining stable on this local macOS MPS machine with `yolov8n` at `512x512`.

## Problem Summary

The current formal run `electric-score-v2-formal-recall-v1-20260424_130711` is not a valid path to a high-score detector:

1. It uses a recall-first rebalanced training set that shifts the train distribution too far away from the unchanged validation split.
2. `optimizer=auto` selected `MuSGD(lr=0.01, momentum=0.9)`, which is materially more aggressive than the earlier stable `AdamW` baseline.
3. Warmup pushed the effective learning rate upward in the first three epochs, while validation metrics collapsed instead of recovering.

Observed validation metrics from the failed run:

- Epoch 1: `mAP50=0.29258`, `mAP50-95=0.13706`, `recall=0.30663`
- Epoch 2: `mAP50=0.08622`, `mAP50-95=0.04327`, `recall=0.10068`
- Epoch 3: `mAP50=0.07702`, `mAP50-95=0.03267`, `recall=0.10252`

This is not healthy early-stage noise. It is a training policy failure for the stated objective.

## Success Criteria

The rebuild is successful only if all of the following are true:

- The new formal training path uses a detector profile explicitly tuned for high validation `mAP`.
- Validation runs every epoch and is written to stable, machine-readable logs.
- The first 5 epochs show a non-collapsing trend on `mAP50`, `mAP50-95`, and recall.
- `optimizer=auto` is no longer allowed to silently choose `MuSGD` for the formal run.
- The final run exports a `best.pt` whose reported metrics are tied to the exact merged dataset artifact used for training.

Target band remains:

- `mAP50 ~= 0.7`
- `mAP50-95 ~= 0.5`

This design does not assume the current dataset can already reach that band. It is focused on restoring a trustworthy optimization path toward it.

## Scope

This work covers:

- replacing the failed recall-first formal run with a high-mAP-first training profile
- rebuilding a new merged training dataset variant for detector scoring
- tightening YOLO label cleaning and source-quality filtering
- adding explicit optimizer and training-profile controls
- expanding monitoring so every epoch can be judged quickly

This work does not cover:

- changing the 7-class detector taxonomy
- replacing `yolov8n` with a larger detector by default
- changing frontend scoring behavior
- changing the non-YOLO score model architecture

## Fixed Constraints

The new design must respect the user's current environment:

- hardware: local Apple Silicon MPS machine
- detector family: `yolov8n`
- image size: `512x512`
- class count: 7 existing power-domain superclasses
- validation split: keep current real validation split unchanged

## High-Level Strategy

The next training path will be `mAP-first`, not `recall-first`.

That means:

1. Build a cleaner merged dataset variant with only moderate class balancing.
2. Train with an explicit stable optimizer and a conservative early learning-rate profile.
3. Run a short health-check training before committing to the full 100-epoch run.
4. Only start the long formal run if the short run shows that the detector is not collapsing.

## Data Strategy

### Validation and test policy

- Keep `val` and `test` untouched so metric comparisons remain meaningful.
- Never apply the new balancing logic to validation or test.

### Training-set rebuild policy

Create a new merged detector dataset variant, separate from both:

- the original cleaned merged dataset
- the current `recall-v1` oversampled dataset

This new dataset should:

- preserve the 7-class taxonomy
- remove empty, corrupt, duplicate, clipped-to-zero, and malformed YOLO labels
- remove images whose labels become empty after cleaning
- optionally filter ultra-small boxes that contribute more noise than signal
- rebalance weak classes only moderately instead of aggressively repeating them

Moderate balancing means:

- no extreme repeat factors like `x8`
- no train distribution that becomes visibly detached from validation
- prefer per-source or per-class caps over brute-force duplication

### Source quality policy

The rebuild should record source-level counts and allow the pipeline to suppress clearly harmful sources if they dominate low-quality annotations.

Each merged dataset summary must include:

- image counts by split
- instance counts by class
- image counts by source
- exact merged dataset path used by training

## Training Strategy

### Formal optimizer policy

The formal high-mAP run must stop using `optimizer=auto`.

Instead:

- choose `AdamW` explicitly for the formal run
- use a conservative fixed learning-rate profile for the first epochs
- keep batch size small enough for stable MPS execution

The main purpose is to prevent the exact failure mode seen in the recall-first run, where `MuSGD` plus fast warmup destroyed validation recall and `mAP`.

### Formal training profile

The formal high-mAP profile should use:

- `model=yolov8n.pt`
- `imgsz=512`
- `val=True`
- validation every epoch
- saved weights every epoch or at least stable `best.pt` plus `last.pt`
- moderate augmentation only
- no recall-first oversampling profile
- no hidden optimizer substitution

### Two-stage execution

#### Stage 1: health check

Run a short formal preflight, nominally 5 epochs, on the new high-mAP dataset/profile.

Pass conditions:

- no immediate `mAP` collapse across the first few epochs
- recall does not fall toward the `0.10` band seen in the failed run
- validation loss does not degrade monotonically

Fail conditions:

- `mAP50` continues to drop after epoch 1 without recovery
- `mAP50-95` collapses similarly
- recall remains near `0.10`

If the health check fails, do not launch the 100-epoch formal run.

#### Stage 2: formal run

Only after a healthy preflight:

- launch the 100-epoch formal run
- keep the same dataset, optimizer family, and logging contract
- monitor every epoch and stop if the run clearly regresses

## Monitoring and Reporting

Per-epoch monitoring must become first-class instead of best-effort.

The training flow must produce:

- `results.csv`
- `yolo_epoch_metrics.jsonl`
- a compact dataset summary for the exact run
- enough metadata to reproduce the run configuration

Each epoch entry must include:

- epoch
- precision
- recall
- `mAP50`
- `mAP50-95`
- path to the evaluated weights

If possible, extend reporting to include per-class AP so low-performing classes can be identified without rerunning analysis.

## Stop and Restart Rules

The previous recall-first formal run is no longer the active path and should not be used as the source of truth for model quality.

The new training workflow must support these operational rules:

- stop early if a health-check run clearly collapses
- never promote `last.pt` from a collapsing run as the new baseline
- only compare future runs against stable validation metrics, not train loss alone

## Files Expected To Change

The implementation is expected to center on:

- `python-ai-service/training/scoring/config.py`
- `python-ai-service/training/scoring/pipeline.py`
- `python-ai-service/training/scoring/yolo_dataset_tools.py`
- `python-ai-service/scripts/repair_yolo_merged_dataset.py`
- `python-ai-service/scripts/monitor_yolo_epoch_metrics.py`

Tests should be added or updated around:

- dataset cleaning and rebuild logic
- training-profile serialization
- epoch-metric reporting

## Risks and Mitigations

- Risk: the current 7-class dataset still has a hard metric ceiling below the target band
  - Mitigation: make the training path trustworthy first, then judge the real dataset ceiling from healthy runs

- Risk: MPS validation remains slow and noisy because of NMS time limits
  - Mitigation: keep batch sizes conservative and ensure every epoch still lands in durable logs

- Risk: moderate balancing is still insufficient for the weakest classes
  - Mitigation: iterate on bounded reweighting after observing per-class AP, not before

- Risk: unrelated local workspace changes make reproducibility harder
  - Mitigation: keep all new run outputs and summaries under the existing training tree with explicit paths

## Decision

Proceed with a new `high-mAP` YOLO rebuild path and treat the current recall-first formal run as an invalid optimization branch rather than a candidate final model.
