import json
from pathlib import Path


def test_build_output_inventory_contains_expected_thesis_files():
    from training.reporting.thesis_figure_config import expected_figure_inventory

    inventory = expected_figure_inventory()

    assert len(inventory) == 29
    assert inventory[0].filename == "01_generation_prompt_overview_grid.png"
    assert inventory[-1].filename == "29_generation_time_compare.png"
    assert inventory[26].filename == "27_multidim_score_heatmap_model_compare.png"
    assert inventory[26].title == "多维度评分热力图（SD1.5 基础版 vs 电力专精版，V1/V2 对照）"
    assert inventory[27].filename == "28_prompt_win_count_compare.png"
    assert inventory[13].title == "自训练评分模型训练损失曲线"


def test_build_model_compare_heatmap_matrix_returns_two_model_columns():
    from training.reporting.thesis_figure_rendering import _build_model_compare_heatmap_matrix

    records = []
    for prompt_index in range(1, 9):
        for offset, model_name in enumerate(("sd15-electric", "sd15-electric-specialized"), start=1):
            base = prompt_index * 10 + offset
            records.append(
                {
                    "prompt_index": prompt_index,
                    "model_name": model_name,
                    "scores": {
                        "electric-score-v2": {
                            "visual_fidelity": base + 0.1,
                            "text_consistency": base + 0.2,
                            "physical_plausibility": base + 0.3,
                            "composition_aesthetics": base + 0.4,
                            "total_score": base + 0.5,
                        }
                    },
                }
            )

    matrix, row_labels, col_labels = _build_model_compare_heatmap_matrix(
        records,
        scoring_model_name="electric-score-v2",
        model_names=["sd15-electric", "sd15-electric-specialized"],
    )

    assert matrix.shape == (8, 10)
    assert row_labels == [f"P{index:02d}" for index in range(1, 9)]
    assert col_labels[0] == "sd15-electric-visual_fidelity"
    assert col_labels[-1] == "sd15-electric-specialized-total_score"
    assert matrix[0][0] == 11.1
    assert matrix[0][-1] == 12.5


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
