def test_build_scoring_service_releases_runtime_after_batch_by_default():
    from app.dependencies import build_scoring_service

    service = build_scoring_service()

    assert service._release_after_batch is True


def test_build_scoring_service_honors_explicit_release_override():
    from app.dependencies import build_scoring_service

    service = build_scoring_service(release_after_batch=False)

    assert service._release_after_batch is False


def test_build_scoring_service_wires_self_trained_bundle_runtime():
    from app.dependencies import build_scoring_service

    service = build_scoring_service()

    assert service._bundle_runtime is not None


def test_build_scoring_service_prefers_gpt_physical_runtime_by_default_when_key_is_available():
    from app.core.settings import Settings
    from app.dependencies import build_scoring_service

    service = build_scoring_service(
        settings=Settings(
            openai_api_key="test-key",
            openai_base_url="https://example.com/v1",
            gpt_physical_enabled=True,
        )
    )

    runtime = service._bundle_runtime._runtimes["electric-score-v2"]

    assert runtime._physical_gpt_runtime is not None
    assert runtime._physical_gpt_runtime._model == "gpt-5.4"


def test_build_scoring_service_can_disable_gpt_physical_runtime_explicitly():
    from app.core.settings import Settings
    from app.dependencies import build_scoring_service

    service = build_scoring_service(
        settings=Settings(
            openai_api_key="test-key",
            openai_base_url="https://example.com/v1",
            gpt_physical_enabled=False,
        )
    )

    runtime = service._bundle_runtime._runtimes["electric-score-v2"]

    assert runtime._physical_gpt_runtime is None


def test_python_runtime_exposes_pkg_resources():
    import pkg_resources

    assert pkg_resources is not None
