# Thesis Figure Package Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reproducible offline figure-generation pipeline that renders the full thesis image package into `docs/image/` from existing prompts, logs, generated images, and scoring outputs.

**Architecture:** Add a small Python reporting package under `python-ai-service/training/reporting/` that centralizes prompt configuration, log parsing, scoring aggregation, and Matplotlib rendering. Expose a single CLI script under `python-ai-service/scripts/` to generate raw figures plus a machine-readable manifest, with pytest coverage for prompt selection, metrics extraction, and output inventory generation.

**Tech Stack:** Python 3.13, Matplotlib, Pillow, NumPy, pytest, existing `python-ai-service` bootstrap/import conventions

---

## File Structure

**Files:**
- Create: `python-ai-service/training/reporting/__init__.py`
- Create: `python-ai-service/training/reporting/thesis_figure_config.py`
- Create: `python-ai-service/training/reporting/thesis_figure_data.py`
- Create: `python-ai-service/training/reporting/thesis_figure_rendering.py`
- Create: `python-ai-service/scripts/generate_thesis_figures.py`
- Create: `python-ai-service/tests/test_thesis_figure_data.py`
- Create: `python-ai-service/tests/test_thesis_figure_rendering.py`
- Modify: `python-ai-service/requirements.txt`
- Output directory: `docs/image/`
- Output metadata: `docs/image/figure_manifest.json`

`thesis_figure_config.py` owns the fixed 8 prompts, unified negative prompt, model names, color palette, figure titles, and filename inventory. `thesis_figure_data.py` owns parsing and aggregation for generation logs, scoring metrics, YOLO CSV metrics, runtime timings, and prompt-level result matrices. `thesis_figure_rendering.py` owns Matplotlib layout helpers, image grid composition, chart rendering, and manifest assembly. `generate_thesis_figures.py` is the only CLI entrypoint and should call into the reporting package with repo-root-aware defaults.

### Task 1: Add Failing Tests For Figure Data And Rendering Contracts

**Files:**
- Create: `python-ai-service/tests/test_thesis_figure_data.py`
- Create: `python-ai-service/tests/test_thesis_figure_rendering.py`

- [ ] **Step 1: Write the failing data extraction tests**

```python
from pathlib import Path


def test_load_prompt_suite_returns_fixed_eight_prompts():
    from training.reporting.thesis_figure_config import build_prompt_suite

    suite = build_prompt_suite()

    assert suite.seed == 42
    assert len(suite.prompts) == 8
    assert suite.negative_prompt.startswith("cartoon, CGI, illustration")
    assert "sd15-electric-specialized" in suite.generation_models


def test_parse_generation_training_log_extracts_loss_lr_and_progress(tmp_path: Path):
    from training.reporting.thesis_figure_data import parse_generation_training_log

    log_path = tmp_path / "training.log"
    log_path.write_text(
        "Steps:   0%|          | 0/500 [00:03<?, ?it/s, lr=0, step_loss=0.356]\\n"
        "Steps:   1%|          | 3/500 [00:48<2:08:43, 15.54s/it, lr=7.5e-7, step_loss=0.00447]\\n",
        encoding="utf-8",
    )

    rows = parse_generation_training_log(log_path)

    assert len(rows) == 2
    assert rows[0].learning_rate == 0.0
    assert rows[1].step == 3
    assert rows[1].step_loss == 0.00447


def test_load_yolo_results_builds_metric_series(tmp_path: Path):
    from training.reporting.thesis_figure_data import load_yolo_results

    csv_path = tmp_path / "results.csv"
    csv_path.write_text(
        "epoch,time,train/box_loss,train/cls_loss,train/dfl_loss,metrics/precision(B),metrics/recall(B),metrics/mAP50(B),metrics/mAP50-95(B),val/box_loss,val/cls_loss,val/dfl_loss,lr/pg0,lr/pg1,lr/pg2\\n"
        "1,10.0,2.1,4.4,1.8,0.1,0.2,0.3,0.15,0,0,0,0.001,0.001,0.001\\n",
        encoding="utf-8",
    )

    rows = load_yolo_results(csv_path)

    assert len(rows) == 1
    assert rows[0].epoch == 1
    assert rows[0].map50 == 0.3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/bin/python -m pytest python-ai-service/tests/test_thesis_figure_data.py -v`

Expected: FAIL with `ModuleNotFoundError` or `ImportError` for `training.reporting`

- [ ] **Step 3: Write the failing rendering and manifest tests**

```python
import json
from pathlib import Path


def test_build_output_inventory_contains_expected_thesis_files():
    from training.reporting.thesis_figure_config import expected_figure_inventory

    inventory = expected_figure_inventory()

    assert len(inventory) == 28
    assert inventory[0].filename == "01_generation_prompt_overview_grid.png"
    assert inventory[-1].filename == "28_generation_time_compare.png"


def test_write_figure_manifest_serializes_title_and_section(tmp_path: Path):
    from training.reporting.thesis_figure_config import FigureSpec
    from training.reporting.thesis_figure_rendering import write_figure_manifest

    manifest_path = tmp_path / "figure_manifest.json"
    write_figure_manifest(
        manifest_path,
        [
            FigureSpec(
                filename="10_generation_training_loss_curve.png",
                title="生成模型训练损失曲线",
                section="生成模型训练结果分析",
                source="model/training/generation/sd15-electric-specialized-v2/training.log",
            )
        ],
    )

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload[0]["title"] == "生成模型训练损失曲线"
    assert payload[0]["section"] == "生成模型训练结果分析"
```

- [ ] **Step 4: Run test to verify it fails**

Run: `./.venv/bin/python -m pytest python-ai-service/tests/test_thesis_figure_rendering.py -v`

Expected: FAIL with `ModuleNotFoundError` or missing symbol errors for reporting helpers

- [ ] **Step 5: Commit**

```bash
git add python-ai-service/tests/test_thesis_figure_data.py python-ai-service/tests/test_thesis_figure_rendering.py
git commit -m "test: define thesis figure pipeline contracts"
```

### Task 2: Implement Prompt Suite, Figure Inventory, And Data Loaders

**Files:**
- Create: `python-ai-service/training/reporting/__init__.py`
- Create: `python-ai-service/training/reporting/thesis_figure_config.py`
- Create: `python-ai-service/training/reporting/thesis_figure_data.py`
- Test: `python-ai-service/tests/test_thesis_figure_data.py`

- [ ] **Step 1: Write minimal config and loader implementation**

```python
# python-ai-service/training/reporting/thesis_figure_config.py
from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class PromptSuite:
    prompts: list[str]
    negative_prompt: str
    generation_models: list[str]
    scoring_models: list[str]
    seed: int


@dataclass(slots=True)
class FigureSpec:
    filename: str
    title: str
    section: str
    source: str


def build_prompt_suite() -> PromptSuite:
    return PromptSuite(
        prompts=[
            "modern electrical substation yard, high-voltage breakers and transformers, stainless steel busbars, gravel ground, safety fencing, warning signage sharp and legible, tidy cables, cinematic depth of field",
            "aerial view of steel lattice transmission towers marching across landscape, taut conductors, wide right-of-way, realistic insulators, rolling terrain, clear sky",
            "grid control room, wall of SCADA screens, operators at desks, LED status panels, cool white lighting, cable management neat, reflective floor, photorealistic optics",
            "utility-scale wind turbines on gentle hills, aligned rows, late afternoon sun, long shadows, crisp blades, realistic nacelles, minimal haze",
            "large photovoltaic farm, endless rows of blue PV panels, tracked mounting racks, clean gravel paths, cable trays, realistic inverters, midday sun",
            "massive concrete hydroelectric dam, spillway gates, turbulent discharge water, mist, safety railings, mountain backdrop, overcast soft light",
            "linemen performing night maintenance on transmission tower, bucket truck, headlamps, portable work lights casting rim light, reflective safety vests, visible harnesses, wet asphalt after rain",
            "wind turbines on grassland, modern wind power station, tall white turbine, clear sky, sunlight, realistic, clean composition, high detail, cinematic lighting",
        ],
        negative_prompt="cartoon, CGI, illustration, painting, anime, over-saturated, over-sharpened, blurry, soft-focus, noise, grainy, jpeg artifacts, banding, chromatic aberration, halos, lens dirt, water spots, duplicate structures, warped geometry, distorted text, gibberish signage, misaligned labels, deformed faces, deformed hands, extra limbs, floating objects",
        generation_models=["sd15-electric", "sd15-electric-specialized", "ssd1b-electric"],
        scoring_models=["electric-score-v1", "electric-score-v2"],
        seed=42,
    )
```

```python
# python-ai-service/training/reporting/thesis_figure_data.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import csv
import re


@dataclass(slots=True)
class GenerationLogRow:
    step: int
    total_steps: int
    elapsed_seconds: float
    seconds_per_iteration: float | None
    iterations_per_second: float | None
    learning_rate: float
    step_loss: float


GENERATION_STEP_PATTERN = re.compile(
    r"Steps:\\s+\\d+%\\|.*?\\|\\s*(\\d+)/(\\d+)\\s*\\[(\\d+):(\\d+):(\\d+)<[^,]*,\\s*([^\\]]+?),\\s*lr=([0-9.eE+-]+),\\s*step_loss=([0-9.eE+-]+)\\]"
)
```

- [ ] **Step 2: Run tests to verify config and loaders pass**

Run: `./.venv/bin/python -m pytest python-ai-service/tests/test_thesis_figure_data.py -v`

Expected: PASS for fixed prompt suite and basic log/CSV parsing

- [ ] **Step 3: Extend inventory definitions and scoring metrics extraction**

```python
def expected_figure_inventory() -> list[FigureSpec]:
    inventory = [
        FigureSpec("01_generation_prompt_overview_grid.png", "固定 Prompt 集生成结果总览", "生成结果对比", "docs/image"),
        *[
            FigureSpec(
                f"{index + 2:02d}_generation_prompt_{index + 1:02d}_model_compare.png",
                f"Prompt {index + 1} 生成结果对比图",
                "生成结果对比",
                "docs/image",
            )
            for index in range(8)
        ],
        FigureSpec("10_generation_training_loss_curve.png", "生成模型训练损失曲线", "生成模型训练结果分析", "model/training/generation/sd15-electric-specialized-v2/training.log"),
        FigureSpec("11_generation_lr_decay_curve.png", "生成模型学习率衰减曲线", "生成模型训练结果分析", "model/training/generation/sd15-electric-specialized-v2/training.log"),
        FigureSpec("12_generation_progress_throughput_curve.png", "生成模型训练进度与吞吐率图", "生成模型训练结果分析", "model/training/generation/sd15-electric-specialized-v2/training.log"),
        FigureSpec("13_scoring_pipeline_baseline_vs_student.png", "主流评分模型组合基线与自训练评分器结构对比", "评分模型设计", "python-ai-service/app/services/scoring_service.py"),
        FigureSpec("14_scoring_v2_training_loss_curve.png", "自训练评分模型训练损失曲线", "评分模型训练结果分析", "model/training/scoring/electric-score-v2/history.json"),
        FigureSpec("15_scoring_v2_lr_curve.png", "自训练评分模型学习率曲线", "评分模型训练结果分析", "python-ai-service/training/scoring/config.py"),
        FigureSpec("16_scoring_v2_progress_curve.png", "自训练评分模型训练进度图", "评分模型训练结果分析", "model/training/scoring/electric-score-v2/history.json"),
        FigureSpec("17_scoring_v2_regression_mae.png", "自训练评分模型各维度回归误差图", "评分模型训练结果分析", "model/scoring/electric-score-v2/metrics.json"),
        FigureSpec("18_yolo_training_loss_curve.png", "YOLO 辅助检测训练损失曲线", "辅助检测模型训练结果分析", "model/training/scoring/electric-score-v2/yolo-mps-compact-noval/train100/results.csv"),
        FigureSpec("19_yolo_lr_curve.png", "YOLO 辅助检测学习率曲线", "辅助检测模型训练结果分析", "model/training/scoring/electric-score-v2/yolo-mps-compact-noval/train100/results.csv"),
        FigureSpec("20_yolo_progress_throughput_curve.png", "YOLO 辅助检测训练进度与吞吐率图", "辅助检测模型训练结果分析", "model/training/scoring/electric-score-v2/yolo-mps-compact-noval/train100/results.csv"),
        FigureSpec("21_yolo_detection_metrics.png", "YOLO 辅助检测指标图", "辅助检测模型训练结果分析", "model/scoring/electric-score-v2/metrics.json"),
        FigureSpec("22_average_total_score_compare.png", "固定 Prompt 集平均总分对比图", "实验结果对比", "docs/image"),
        FigureSpec("23_dimension_gain_compare.png", "各维度增益对比图", "实验结果对比", "docs/image"),
        FigureSpec("24_total_score_boxplot.png", "总分箱线图", "实验结果对比", "docs/image"),
        FigureSpec("25_multidim_score_heatmap_v1.png", "多维度评分热力图（基线评分器）", "实验结果对比", "docs/image"),
        FigureSpec("26_multidim_score_heatmap_v2.png", "多维度评分热力图（自训练评分器）", "实验结果对比", "docs/image"),
        FigureSpec("27_prompt_win_count_compare.png", "固定 Prompt 集获胜次数统计图", "实验结果对比", "docs/image"),
        FigureSpec("28_generation_time_compare.png", "生成耗时对比图", "实验结果对比", "docs/image"),
    ]
    return inventory


def load_scoring_v2_history(path: Path) -> list[dict[str, float]]:
    import json

    return json.loads(path.read_text(encoding="utf-8"))


def load_scoring_v2_metrics(path: Path) -> dict[str, object]:
    import json

    return json.loads(path.read_text(encoding="utf-8"))
```

- [ ] **Step 4: Re-run tests to verify data layer stays green**

Run: `./.venv/bin/python -m pytest python-ai-service/tests/test_thesis_figure_data.py -v`

Expected: PASS with all assertions green

- [ ] **Step 5: Commit**

```bash
git add python-ai-service/training/reporting/__init__.py python-ai-service/training/reporting/thesis_figure_config.py python-ai-service/training/reporting/thesis_figure_data.py python-ai-service/tests/test_thesis_figure_data.py
git commit -m "feat: add thesis figure data loaders"
```

### Task 3: Implement Matplotlib Rendering Helpers And CLI Entry Point

**Files:**
- Create: `python-ai-service/training/reporting/thesis_figure_rendering.py`
- Create: `python-ai-service/scripts/generate_thesis_figures.py`
- Modify: `python-ai-service/requirements.txt`
- Test: `python-ai-service/tests/test_thesis_figure_rendering.py`

- [ ] **Step 1: Add pinned Matplotlib dependency**

```text
# python-ai-service/requirements.txt
matplotlib==3.10.8
```

- [ ] **Step 2: Implement rendering and manifest helpers**

```python
# python-ai-service/training/reporting/thesis_figure_rendering.py
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt


def write_figure_manifest(path: Path, figure_specs: list) -> None:
    payload = [
        {
            "filename": spec.filename,
            "title": spec.title,
            "section": spec.section,
            "source": spec.source,
        }
        for spec in figure_specs
    ]
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def ensure_output_dirs(root: Path) -> dict[str, Path]:
    return {
        "generation_comparison": root / "generation-comparison",
        "generation_training": root / "generation-training",
        "scoring_training": root / "scoring-training",
        "evaluation_stats": root / "evaluation-stats",
        "paper_ready": root / "paper-ready",
    }
```

- [ ] **Step 3: Implement CLI that renders all 28 figures**

```python
# python-ai-service/scripts/generate_thesis_figures.py
from __future__ import annotations

import argparse

try:
    from scripts.bootstrap import ensure_project_root_on_path
except ImportError:
    from bootstrap import ensure_project_root_on_path

ensure_project_root_on_path()

from training.reporting.thesis_figure_rendering import generate_thesis_figure_package


def main() -> int:
    parser = argparse.ArgumentParser(description="Render thesis-ready generation and scoring figures.")
    parser.add_argument("--runtime-root", default="model")
    parser.add_argument("--output-dir", default="docs/image")
    args = parser.parse_args()
    generate_thesis_figure_package(runtime_root=args.runtime_root, output_dir=args.output_dir)
    return 0
```

- [ ] **Step 4: Run rendering tests to verify they pass**

Run: `./.venv/bin/python -m pytest python-ai-service/tests/test_thesis_figure_rendering.py -v`

Expected: PASS for inventory length and manifest serialization

- [ ] **Step 5: Commit**

```bash
git add python-ai-service/requirements.txt python-ai-service/training/reporting/thesis_figure_rendering.py python-ai-service/scripts/generate_thesis_figures.py python-ai-service/tests/test_thesis_figure_rendering.py
git commit -m "feat: add thesis figure rendering pipeline"
```

### Task 4: Generate Real Figure Outputs From Repository Artifacts

**Files:**
- Output: `docs/image/generation-comparison/*.png`
- Output: `docs/image/generation-training/*.png`
- Output: `docs/image/scoring-training/*.png`
- Output: `docs/image/evaluation-stats/*.png`
- Output: `docs/image/paper-ready/*.png`
- Output: `docs/image/figure_manifest.json`

- [ ] **Step 1: Run the full figure generation CLI**

Run:

```bash
./.venv/bin/python python-ai-service/scripts/generate_thesis_figures.py \
  --runtime-root model \
  --output-dir docs/image
```

Expected: exit `0` and freshly written figures plus `docs/image/figure_manifest.json`

- [ ] **Step 2: Verify the expected files exist**

Run:

```bash
find docs/image -type f | sort
```

Expected: includes the 28 requested PNGs and the manifest JSON

- [ ] **Step 3: Open manifest and confirm all titles and sources serialize correctly**

Run:

```bash
./.venv/bin/python - <<'PY'
import json
from pathlib import Path
payload = json.loads(Path("docs/image/figure_manifest.json").read_text(encoding="utf-8"))
print(len(payload))
print(payload[0]["filename"], payload[0]["title"])
print(payload[-1]["filename"], payload[-1]["title"])
PY
```

Expected: prints `28` plus the first and last figure entries

- [ ] **Step 4: Commit generated figure package artifacts**

```bash
git add docs/image python-ai-service/scripts/generate_thesis_figures.py python-ai-service/training/reporting python-ai-service/requirements.txt python-ai-service/tests/test_thesis_figure_data.py python-ai-service/tests/test_thesis_figure_rendering.py
git commit -m "feat: generate thesis figure package"
```

### Task 5: Full Verification And Delivery Checklist

**Files:**
- Verify: `docs/image/figure_manifest.json`
- Verify: `docs/image/paper-ready/`
- Verify: `docs/superpowers/specs/2026-04-18-thesis-figure-package-design.md`

- [ ] **Step 1: Run the targeted pytest suite fresh**

Run:

```bash
./.venv/bin/python -m pytest \
  python-ai-service/tests/test_thesis_figure_data.py \
  python-ai-service/tests/test_thesis_figure_rendering.py -v
```

Expected: all tests PASS

- [ ] **Step 2: Re-run the figure generation command fresh**

Run:

```bash
./.venv/bin/python python-ai-service/scripts/generate_thesis_figures.py \
  --runtime-root model \
  --output-dir docs/image
```

Expected: exit `0` with regenerated figures and manifest

- [ ] **Step 3: Verify inventory count and representative output paths**

Run:

```bash
./.venv/bin/python - <<'PY'
import json
from pathlib import Path
payload = json.loads(Path("docs/image/figure_manifest.json").read_text(encoding="utf-8"))
assert len(payload) == 28
required = [
    Path("docs/image/generation-comparison/01_generation_prompt_overview_grid.png"),
    Path("docs/image/generation-training/10_generation_training_loss_curve.png"),
    Path("docs/image/scoring-training/14_scoring_v2_training_loss_curve.png"),
    Path("docs/image/evaluation-stats/22_average_total_score_compare.png"),
]
for path in required:
    assert path.exists(), path
print("inventory-ok", len(payload))
PY
```

Expected: prints `inventory-ok 28`

- [ ] **Step 4: Commit final verification-only changes if needed**

```bash
git add docs/image/figure_manifest.json
git commit -m "chore: refresh thesis figure outputs"
```
