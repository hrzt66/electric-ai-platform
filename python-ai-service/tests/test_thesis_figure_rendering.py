import json
from pathlib import Path


def test_build_output_inventory_contains_expected_thesis_files():
    from training.reporting.thesis_figure_config import expected_figure_inventory

    inventory = expected_figure_inventory()

    assert len(inventory) == 28
    assert inventory[0].filename == "01_generation_prompt_overview_grid.png"
    assert inventory[-1].filename == "28_generation_time_compare.png"
    assert inventory[13].title == "自训练评分模型训练损失曲线"


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
    assert payload[0]["filename"] == "10_generation_training_loss_curve.png"
    assert payload[0]["title"] == "生成模型训练损失曲线"
    assert payload[0]["section"] == "生成模型训练结果分析"
    assert payload[0]["source"].endswith("training.log")


def test_ensure_output_dirs_creates_expected_children(tmp_path: Path):
    from training.reporting.thesis_figure_rendering import ensure_output_dirs

    output_dirs = ensure_output_dirs(tmp_path)

    assert set(output_dirs) == {
        "generation_comparison",
        "generation_training",
        "scoring_training",
        "evaluation_stats",
        "paper_ready",
    }
    for path in output_dirs.values():
        assert isinstance(path, Path)
