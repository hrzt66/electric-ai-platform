def test_image_reward_runtime_normalizes_zero_to_mid_score():
    from app.runtimes.scorers.image_reward_runtime import ImageRewardRuntime

    runtime = ImageRewardRuntime(device="cpu")

    assert runtime.normalize_score(0.0) == 50.0


def test_aesthetic_runtime_uses_piecewise_normalization():
    from app.runtimes.scorers.aesthetic_runtime import AestheticRuntime

    runtime = AestheticRuntime(device="cpu")

    assert runtime.normalize_score(5.0) == 60.0


def test_aesthetic_runtime_extracts_filename_from_windows_path():
    from app.runtimes.scorers.aesthetic_runtime import _extract_weight_filename

    assert _extract_weight_filename(r"E:\毕业设计\源代码\Project\sac+logos+ava1-l14-linearMSE.pth") == "sac+logos+ava1-l14-linearMSE.pth"


def test_clip_iqa_runtime_balanced_probabilities_return_mid_score():
    from app.runtimes.scorers.clip_iqa_runtime import ClipIQARuntime

    runtime = ClipIQARuntime(mode="visual_fidelity", device="cpu")

    assert runtime.normalize_probability_score(0.5, 0.5) == 50.0
