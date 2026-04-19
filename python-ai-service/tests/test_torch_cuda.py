import sys


def test_preferred_torch_device_type_prefers_cuda_over_mps(monkeypatch):
    from app.core import torch_cuda

    class FakeTorch:
        class cuda:
            @staticmethod
            def is_available() -> bool:
                return True

        class backends:
            class mps:
                @staticmethod
                def is_available() -> bool:
                    return True

    monkeypatch.setitem(sys.modules, "torch", FakeTorch)

    assert torch_cuda.preferred_torch_device_type() == "cuda"


def test_preferred_torch_device_type_uses_mps_when_cuda_missing(monkeypatch):
    from app.core import torch_cuda

    class FakeTorch:
        class cuda:
            @staticmethod
            def is_available() -> bool:
                return False

        class backends:
            class mps:
                @staticmethod
                def is_available() -> bool:
                    return True

    monkeypatch.setitem(sys.modules, "torch", FakeTorch)

    assert torch_cuda.preferred_torch_device_type() == "mps"


def test_best_effort_cleanup_torch_calls_mps_empty_cache(monkeypatch):
    from app.core import torch_cuda

    calls = []

    class FakeTorch:
        class cuda:
            @staticmethod
            def is_available() -> bool:
                return False

        class backends:
            class mps:
                @staticmethod
                def is_available() -> bool:
                    return True

        class mps:
            @staticmethod
            def empty_cache() -> None:
                calls.append("empty_cache")

    monkeypatch.setitem(sys.modules, "torch", FakeTorch)

    torch_cuda.best_effort_cleanup_torch()

    assert calls == ["empty_cache"]
