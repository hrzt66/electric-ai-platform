from textwrap import dedent


def test_parse_prompt_module_text_extracts_prompts_and_negative_prompt():
    from app.benchmark_utils import parse_prompt_module_text

    prompt_set = parse_prompt_module_text(
        dedent(
            """
            export const RECOMMENDED_POSITIVE_PROMPTS = [
              'first prompt',
              'second prompt',
            ] as const

            export const RECOMMENDED_NEGATIVE_PROMPT =
              'bad anatomy, blurry'
            """
        )
    )

    assert prompt_set.positive_prompts == ["first prompt", "second prompt"]
    assert prompt_set.negative_prompt == "bad anatomy, blurry"


def test_parse_generation_training_log_keeps_latest_row_per_step():
    from app.benchmark_utils import parse_generation_training_log

    rows = parse_generation_training_log(
        dedent(
            """
            Steps:   0%|          | 0/8000 [00:01<?, ?it/s, lr=0, step_loss=0.674]
            Steps:   0%|          | 0/8000 [00:04<?, ?it/s, lr=0, step_loss=0.0297]
            Steps:   0%|          | 1/8000 [00:04<11:03:20,  4.98s/it, lr=5e-7, step_loss=0.133]
            Steps:   0%|          | 1/8000 [00:07<11:03:20,  4.98s/it, lr=5e-7, step_loss=0.0882]
            Steps:   0%|          | 2/8000 [00:08<8:49:25,  3.97s/it, lr=1e-6, step_loss=0.0859]
            """
        )
    )

    assert rows == [
        {"step": 0, "total_steps": 8000, "lr": 0.0, "step_loss": 0.0297},
        {"step": 1, "total_steps": 8000, "lr": 5e-7, "step_loss": 0.0882},
        {"step": 2, "total_steps": 8000, "lr": 1e-6, "step_loss": 0.0859},
    ]


def test_parse_monitor_history_extracts_progress_rows():
    from app.benchmark_utils import parse_monitor_history

    rows = parse_monitor_history(
        dedent(
            """
            [2026-04-07T18:45:23] status=running
            [2026-04-07T18:46:07] status=running step=86/8000 progress=1.08% eta=10:18:01
            [2026-04-07T18:52:26] status=running step=169/8000 progress=2.11% eta=9:07:47
            """
        )
    )

    assert rows == [
        {
            "timestamp": "2026-04-07T18:46:07",
            "step": 86,
            "total_steps": 8000,
            "progress_pct": 1.08,
            "eta": "10:18:01",
        },
        {
            "timestamp": "2026-04-07T18:52:26",
            "step": 169,
            "total_steps": 8000,
            "progress_pct": 2.11,
            "eta": "9:07:47",
        },
    ]


def test_summarize_benchmark_rows_groups_by_generation_and_scorer():
    from app.benchmark_utils import summarize_benchmark_rows

    rows = [
        {
            "generation_model": "sd15-electric",
            "scoring_model": "electric-score-v3",
            "prompt_index": 1,
            "total_score": 70.0,
            "visual_fidelity": 75.0,
            "text_consistency": 68.0,
            "physical_plausibility": 67.0,
            "composition_aesthetics": 71.0,
            "generation_seconds": 12.0,
        },
        {
            "generation_model": "sd15-electric",
            "scoring_model": "electric-score-v3",
            "prompt_index": 2,
            "total_score": 74.0,
            "visual_fidelity": 77.0,
            "text_consistency": 72.0,
            "physical_plausibility": 70.0,
            "composition_aesthetics": 73.0,
            "generation_seconds": 14.0,
        },
        {
            "generation_model": "unipic2-kontext",
            "scoring_model": "electric-score-v3",
            "prompt_index": 1,
            "total_score": 79.0,
            "visual_fidelity": 82.0,
            "text_consistency": 80.0,
            "physical_plausibility": 76.0,
            "composition_aesthetics": 78.0,
            "generation_seconds": 22.0,
        },
    ]

    summary = summarize_benchmark_rows(rows)

    assert summary == [
        {
            "generation_model": "sd15-electric",
            "scoring_model": "electric-score-v3",
            "sample_count": 2,
            "avg_total_score": 72.0,
            "avg_visual_fidelity": 76.0,
            "avg_text_consistency": 70.0,
            "avg_physical_plausibility": 68.5,
            "avg_composition_aesthetics": 72.0,
            "avg_generation_seconds": 13.0,
        },
        {
            "generation_model": "unipic2-kontext",
            "scoring_model": "electric-score-v3",
            "sample_count": 1,
            "avg_total_score": 79.0,
            "avg_visual_fidelity": 82.0,
            "avg_text_consistency": 80.0,
            "avg_physical_plausibility": 76.0,
            "avg_composition_aesthetics": 78.0,
            "avg_generation_seconds": 22.0,
        },
    ]
