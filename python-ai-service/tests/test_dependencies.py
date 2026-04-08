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


def test_python_runtime_exposes_pkg_resources():
    import pkg_resources

    assert pkg_resources is not None
