from scripts import monitor_probe


def test_build_payload_for_macos_includes_preferred_device_and_reason(monkeypatch):
    monkeypatch.setattr(monitor_probe, "detect_mps_available", lambda: True, raising=False)
    monkeypatch.setattr(
        monitor_probe, "detect_preferred_device_type", lambda: "mps", raising=False
    )
    monkeypatch.setattr(
        monitor_probe, "measure_ai_process_memory_bytes", lambda: 987654321, raising=False
    )

    payload = monitor_probe.build_payload("Darwin")

    assert payload["platform_family"] == "macos"
    assert payload["mps_available"] is True
    assert payload["preferred_device_type"] == "mps"
    assert payload["ai_process_memory_bytes"] == 987654321
    assert payload["unavailable_reason"] == ""


def test_build_payload_for_macos_sets_reason_when_mps_is_unavailable(monkeypatch):
    monkeypatch.setattr(monitor_probe, "detect_mps_available", lambda: False, raising=False)
    monkeypatch.setattr(
        monitor_probe, "detect_preferred_device_type", lambda: "cpu", raising=False
    )
    monkeypatch.setattr(
        monitor_probe, "measure_ai_process_memory_bytes", lambda: 0, raising=False
    )

    payload = monitor_probe.build_payload("Darwin")

    assert payload["mps_available"] is False
    assert payload["preferred_device_type"] == "cpu"
    assert payload["unavailable_reason"]


def test_build_payload_for_windows():
    payload = monitor_probe.build_payload("Windows")

    assert payload == {
        "platform_family": "windows",
        "gpu_name": "",
        "vram_total_mb": 0,
        "vram_used_mb": 0,
        "gpu_utilization_percent": 0,
        "temperature_c": 0,
    }
