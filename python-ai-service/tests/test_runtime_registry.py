from pathlib import Path


def test_runtime_registry_marks_sd15_available_when_local_files_exist(tmp_path):
    from app.core.settings import Settings
    from app.runtimes.runtime_registry import RuntimeRegistry

    generation_dir = tmp_path / "generation" / "sd15-electric"
    generation_dir.mkdir(parents=True)
    (generation_dir / "model_index.json").write_text("{}", encoding="utf-8")

    settings = Settings(runtime_root=tmp_path)
    registry = RuntimeRegistry(settings=settings)

    models = registry.list_models()
    sd15 = next(item for item in models["items"] if item["name"] == "sd15-electric")

    assert sd15["status"] == "available"
    assert Path(sd15["local_dir"]) == generation_dir


def test_runtime_registry_marks_unipic2_available_when_local_files_exist(tmp_path):
    from app.core.settings import Settings
    from app.runtimes.runtime_registry import RuntimeRegistry

    generation_dir = tmp_path / "generation" / "unipic2-kontext"
    generation_dir.mkdir(parents=True)
    (generation_dir / "model_index.json").write_text("{}", encoding="utf-8")

    settings = Settings(runtime_root=tmp_path)
    registry = RuntimeRegistry(settings=settings)

    models = registry.list_models()
    unipic2 = next(item for item in models["items"] if item["name"] == "unipic2-kontext")

    assert unipic2["status"] == "available"
    assert Path(unipic2["local_dir"]) == generation_dir


def test_runtime_registry_marks_ssd1b_available_when_local_files_exist(tmp_path):
    from app.core.settings import Settings
    from app.runtimes.runtime_registry import RuntimeRegistry

    generation_dir = tmp_path / "generation" / "ssd1b-electric"
    generation_dir.mkdir(parents=True)
    (generation_dir / "model_index.json").write_text("{}", encoding="utf-8")

    settings = Settings(runtime_root=tmp_path)
    registry = RuntimeRegistry(settings=settings)

    models = registry.list_models()
    ssd1b = next(item for item in models["items"] if item["name"] == "ssd1b-electric")

    assert ssd1b["status"] == "available"
    assert Path(ssd1b["local_dir"]) == generation_dir


def test_runtime_registry_builds_sd15_runtime_from_settings(tmp_path):
    from app.core.settings import Settings
    from app.runtimes.runtime_registry import RuntimeRegistry
    from app.runtimes.sd15_runtime import SD15Runtime

    settings = Settings(runtime_root=tmp_path)
    registry = RuntimeRegistry(settings=settings)

    runtime = registry.get_generation_runtime("sd15-electric")

    assert isinstance(runtime, SD15Runtime)
    assert runtime.model_dir == tmp_path / "generation" / "sd15-electric"


def test_runtime_registry_builds_ssd1b_runtime_from_settings(tmp_path):
    from app.core.settings import Settings
    from app.runtimes.runtime_registry import RuntimeRegistry
    from app.runtimes.ssd1b_runtime import SSD1BRuntime

    settings = Settings(runtime_root=tmp_path)
    registry = RuntimeRegistry(settings=settings)

    runtime = registry.get_generation_runtime("ssd1b-electric")

    assert isinstance(runtime, SSD1BRuntime)
    assert runtime.model_dir == tmp_path / "generation" / "ssd1b-electric"


def test_runtime_registry_builds_specialized_sd15_runtime_from_settings(tmp_path):
    from app.core.settings import Settings
    from app.runtimes.runtime_registry import RuntimeRegistry
    from app.runtimes.sd15_runtime import SD15Runtime

    settings = Settings(runtime_root=tmp_path)
    registry = RuntimeRegistry(settings=settings)

    runtime = registry.get_generation_runtime("sd15-electric-specialized")

    assert isinstance(runtime, SD15Runtime)
    assert runtime.model_dir == tmp_path / "generation" / "sd15-electric-specialized"


def test_runtime_registry_builds_unipic2_runtime_from_settings(tmp_path):
    from app.core.settings import Settings
    from app.runtimes.runtime_registry import RuntimeRegistry
    from app.runtimes.unipic2_runtime import UniPic2Runtime

    settings = Settings(runtime_root=tmp_path)
    registry = RuntimeRegistry(settings=settings)

    runtime = registry.get_generation_runtime("unipic2-kontext")

    assert isinstance(runtime, UniPic2Runtime)
    assert runtime.model_dir == tmp_path / "generation" / "unipic2-kontext"


def test_runtime_registry_switches_generation_runtime_as_single_active(tmp_path):
    from app.core.settings import Settings
    from app.runtimes.runtime_registry import RuntimeRegistry

    class FakeRuntime:
        def __init__(self, name: str) -> None:
            self.name = name
            self.unloaded = False

        def unload(self) -> None:
            self.unloaded = True

    settings = Settings(runtime_root=tmp_path)
    registry = RuntimeRegistry(settings=settings)
    runtimes: dict[str, FakeRuntime] = {}

    registry._generation_runtime_factories = {
        "sd15-electric": lambda: runtimes.setdefault("sd15-electric", FakeRuntime("sd15-electric")),
        "ssd1b-electric": lambda: runtimes.setdefault("ssd1b-electric", FakeRuntime("ssd1b-electric")),
    }

    sd15_runtime = registry.get_generation_runtime("sd15-electric")
    assert registry.get_generation_runtime("sd15-electric") is sd15_runtime
    assert sd15_runtime.unloaded is False

    ssd1b_runtime = registry.get_generation_runtime("ssd1b-electric")

    assert ssd1b_runtime is runtimes["ssd1b-electric"]
    assert sd15_runtime.unloaded is True
    assert registry._runtime_cache == {"ssd1b-electric": ssd1b_runtime}


def test_runtime_registry_releases_requested_generation_runtime(tmp_path):
    from app.core.settings import Settings
    from app.runtimes.runtime_registry import RuntimeRegistry

    class FakeRuntime:
        def __init__(self) -> None:
            self.unloaded = False

        def unload(self) -> None:
            self.unloaded = True

    settings = Settings(runtime_root=tmp_path)
    registry = RuntimeRegistry(settings=settings)
    runtime = FakeRuntime()
    registry._runtime_cache["sd15-electric"] = runtime
    registry._active_generation_model_name = "sd15-electric"

    registry.release_generation_runtime("sd15-electric")

    assert runtime.unloaded is True
    assert registry._runtime_cache == {}
    assert registry._active_generation_model_name is None


def test_runtime_registry_logs_runtime_switch_and_release(tmp_path, caplog):
    from app.core.settings import Settings
    from app.runtimes.runtime_registry import RuntimeRegistry

    class FakeRuntime:
        def __init__(self, name: str) -> None:
            self.name = name
            self.unloaded = False

        def unload(self) -> None:
            self.unloaded = True

    caplog.set_level("INFO", logger="electric_ai.runtime")

    settings = Settings(runtime_root=tmp_path)
    registry = RuntimeRegistry(settings=settings)
    runtimes: dict[str, FakeRuntime] = {}
    registry._generation_runtime_factories = {
        "sd15-electric": lambda: runtimes.setdefault("sd15-electric", FakeRuntime("sd15-electric")),
        "ssd1b-electric": lambda: runtimes.setdefault("ssd1b-electric", FakeRuntime("ssd1b-electric")),
    }

    registry.get_generation_runtime("sd15-electric")
    registry.get_generation_runtime("ssd1b-electric")
    registry.release_generation_runtime()

    messages = "\n".join(record.getMessage() for record in caplog.records)
    assert "building generation runtime model=sd15-electric" in messages
    assert "switching generation runtime from=sd15-electric to=ssd1b-electric" in messages
    assert "releasing generation runtime model=ssd1b-electric" in messages


def test_runtime_registry_lists_specialized_sd15_model(tmp_path):
    from app.core.settings import Settings
    from app.runtimes.runtime_registry import RuntimeRegistry

    generation_dir = tmp_path / "generation" / "sd15-electric-specialized"
    generation_dir.mkdir(parents=True)
    (generation_dir / "model_index.json").write_text("{}", encoding="utf-8")

    settings = Settings(runtime_root=tmp_path)
    registry = RuntimeRegistry(settings=settings)

    items = registry.list_models()["items"]
    specialized = next(item for item in items if item["name"] == "sd15-electric-specialized")

    assert specialized["status"] == "available"
    assert Path(specialized["local_dir"]) == generation_dir
