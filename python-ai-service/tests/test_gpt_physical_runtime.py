from __future__ import annotations

import sys
import types
from pathlib import Path

from PIL import Image

rubric_stub = types.ModuleType("training.scoring.rubric")
rubric_stub.build_prompt_expectation = lambda prompt, _: types.SimpleNamespace(expected_classes={"wind_turbine"})
rubric_stub.canonicalize_detection_class_name = lambda name: name
sys.modules.setdefault("training.scoring.rubric", rubric_stub)

from app.runtimes.scorers.gpt_physical_runtime import GPTPhysicalRuntime


class _FakeResponse:
    def __init__(self, output_text: str) -> None:
        self.output_text = output_text


class _FakeResponsesApi:
    def __init__(self, outcomes: list[object]) -> None:
        self._outcomes = list(outcomes)
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return _FakeResponse(str(outcome))


class _FakeClient:
    def __init__(self, outcomes: list[object]) -> None:
        self.responses = _FakeResponsesApi(outcomes)


def _write_image(path: Path) -> None:
    Image.new("RGB", (16, 16), color=(120, 130, 140)).save(path)


def test_gpt_physical_runtime_retries_failed_requests_and_keeps_gpt_54_model(tmp_path) -> None:
    image_path = tmp_path / "sample.png"
    _write_image(image_path)
    client = _FakeClient(
        [
            RuntimeError("temporary upstream failure"),
            RuntimeError("temporary gateway failure"),
            """
            {"target_class":"wind_turbine","score":91,"reason":"structure is plausible","present_elements":["tower","nacelle","blades"],"missing_elements":[],"rule_checks":[{"label":"叶片数量","passed":true,"detail":"three blades detected"}]}
            """,
        ]
    )
    runtime = GPTPhysicalRuntime(
        output_dir=tmp_path / "annotations",
        api_key="test-key",
        base_url="https://example.com/v1",
        client=client,
    )

    result = runtime.annotate_image(image_path=str(image_path), prompt="realistic wind turbine in a substation yard")

    assert result["model"] == "gpt-5.4"
    assert result["score"] == 91.0
    assert len(client.responses.calls) == 3
    assert all(call["model"] == "gpt-5.4" for call in client.responses.calls)
