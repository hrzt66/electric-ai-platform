from __future__ import annotations

import base64
from types import SimpleNamespace

import pytest


class FakeImagesClient:
    def __init__(self, response) -> None:
        self.response = response
        self.calls: list[dict] = []

    def generate(self, **kwargs):
        self.calls.append(kwargs)
        if isinstance(self.response, list):
            next_item = self.response.pop(0)
            if isinstance(next_item, Exception):
                raise next_item
            return next_item
        return self.response


class FakeOpenAIClient:
    def __init__(self, response) -> None:
        self.images = FakeImagesClient(response)


class FakeTransientGatewayError(RuntimeError):
    def __init__(self, message: str, *, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response = None


def test_openai_image_runtime_saves_base64_image_and_returns_record(tmp_path):
    from app.runtimes.openai_image_runtime import OpenAIImageRuntime

    png_bytes = b"fake-png-bytes"
    client = FakeOpenAIClient({"data": [{"b64_json": base64.b64encode(png_bytes).decode("ascii")}]})
    runtime = OpenAIImageRuntime(
        output_dir=tmp_path,
        api_key="test-key",
        base_url="https://geekspace.cloud/v1",
        image_model="gpt-image-2",
        client_factory=lambda **_: client,
    )

    records = runtime.generate(
        job_id=7,
        prompt="500kV substation",
        negative_prompt="blurry",
        seed=42,
        width=512,
        height=512,
        steps=20,
        guidance_scale=7.5,
        num_images=1,
        model_name="gpt-image-2",
    )

    image_path = tmp_path / "7_0_42.png"
    assert image_path.read_bytes() == png_bytes
    assert records == [
        {
            "file_path": str(image_path),
            "seed": 42,
            "width": 512,
            "height": 512,
            "model_name": "gpt-image-2",
        }
    ]
    assert client.images.calls == [
        {
            "model": "gpt-image-2",
            "prompt": "500kV substation",
            "size": "1024x1024",
        }
    ]


def test_openai_image_runtime_downloads_url_response(tmp_path):
    from app.runtimes.openai_image_runtime import OpenAIImageRuntime

    client = FakeOpenAIClient(SimpleNamespace(data=[SimpleNamespace(url="https://example.test/image.png")]))
    downloads: list[str] = []

    def fake_downloader(url: str) -> bytes:
        downloads.append(url)
        return b"url-png-bytes"

    runtime = OpenAIImageRuntime(
        output_dir=tmp_path,
        api_key="test-key",
        base_url="https://geekspace.cloud/v1",
        image_model="dall-e-2",
        client_factory=lambda **_: client,
        url_downloader=fake_downloader,
    )

    records = runtime.generate(
        job_id=8,
        prompt="wind farm",
        negative_prompt="",
        seed=99,
        width=1024,
        height=1024,
        steps=20,
        guidance_scale=7.5,
        num_images=1,
        model_name="gpt-image-2",
    )

    image_path = tmp_path / "8_0_99.png"
    assert image_path.read_bytes() == b"url-png-bytes"
    assert downloads == ["https://example.test/image.png"]
    assert records[0]["file_path"] == str(image_path)
    assert client.images.calls[0]["response_format"] == "url"


def test_openai_image_runtime_rejects_unsupported_dalle2_size(tmp_path):
    from app.runtimes.openai_image_runtime import OpenAIImageRuntime

    runtime = OpenAIImageRuntime(
        output_dir=tmp_path,
        api_key="test-key",
        base_url="https://geekspace.cloud/v1",
        image_model="dall-e-2",
        client_factory=lambda **_: FakeOpenAIClient({"data": []}),
    )

    with pytest.raises(ValueError, match="DALL-E 2"):
        runtime.generate(
            job_id=9,
            prompt="substation",
            negative_prompt="",
            seed=1,
            width=768,
            height=512,
            steps=20,
            guidance_scale=7.5,
            num_images=1,
            model_name="gpt-image-2",
        )


def test_openai_image_runtime_uses_supported_gpt_image_size_when_requested_dimensions_are_unsupported(tmp_path):
    from app.runtimes.openai_image_runtime import OpenAIImageRuntime

    client = FakeOpenAIClient({"data": [{"b64_json": base64.b64encode(b"fake-png-bytes").decode("ascii")}]})
    runtime = OpenAIImageRuntime(
        output_dir=tmp_path,
        api_key="test-key",
        base_url="https://geekspace.cloud/v1",
        image_model="gpt-image-2",
        client_factory=lambda **_: client,
    )

    runtime.generate(
        job_id=10,
        prompt="future wind farm",
        negative_prompt="ignored",
        seed=1,
        width=1024,
        height=1024,
        steps=20,
        guidance_scale=7.5,
        num_images=1,
        model_name="gpt-image-2",
    )

    assert client.images.calls == [
        {
            "model": "gpt-image-2",
            "prompt": "future wind farm",
            "size": "1024x1024",
        }
    ]


def test_openai_image_runtime_preserves_supported_gpt_image_size(tmp_path):
    from app.runtimes.openai_image_runtime import OpenAIImageRuntime

    client = FakeOpenAIClient({"data": [{"b64_json": base64.b64encode(b"wide-png-bytes").decode("ascii")}]})
    runtime = OpenAIImageRuntime(
        output_dir=tmp_path,
        api_key="test-key",
        base_url="https://www.boxying.com/v1",
        image_model="gpt-image-2",
        client_factory=lambda **_: client,
    )

    runtime.generate(
        job_id=11,
        prompt="wide substation panorama",
        negative_prompt="ignored",
        seed=2,
        width=1536,
        height=1024,
        steps=20,
        guidance_scale=7.5,
        num_images=1,
        model_name="gpt-image-2",
    )

    assert client.images.calls == [
        {
            "model": "gpt-image-2",
            "prompt": "wide substation panorama",
            "size": "1536x1024",
        }
    ]


def test_openai_image_runtime_retries_transient_gateway_errors(tmp_path):
    from app.runtimes.openai_image_runtime import OpenAIImageRuntime

    transient_error = FakeTransientGatewayError(
        "Error code: 503 - {'error': {'message': 'No available compatible accounts'}}",
        status_code=503,
    )
    client = FakeOpenAIClient(
        [
            transient_error,
            transient_error,
            {"data": [{"b64_json": base64.b64encode(b"recovered-png-bytes").decode("ascii")}]},
        ]
    )
    runtime = OpenAIImageRuntime(
        output_dir=tmp_path,
        api_key="test-key",
        base_url="https://www.boxying.com/v1",
        image_model="gpt-image-2",
        client_factory=lambda **_: client,
    )

    records = runtime.generate(
        job_id=12,
        prompt="substation after transient outage",
        negative_prompt="ignored",
        seed=3,
        width=512,
        height=512,
        steps=20,
        guidance_scale=7.5,
        num_images=1,
        model_name="gpt-image-2",
    )

    assert len(records) == 1
    assert len(client.images.calls) == 3


def test_openai_image_runtime_builds_openai_client_with_standalone_compatible_httpx_settings(tmp_path, monkeypatch):
    from app.runtimes.openai_image_runtime import OpenAIImageRuntime

    captured: dict[str, object] = {}

    class FakeHttpxClient:
        def __init__(self, *, trust_env, timeout) -> None:
            captured["trust_env"] = trust_env
            captured["timeout"] = timeout

    class FakeOpenAI:
        def __init__(self, **kwargs) -> None:
            captured.update(kwargs)

    monkeypatch.setattr("app.runtimes.openai_image_runtime.HttpxClient", FakeHttpxClient)
    monkeypatch.setattr("openai.OpenAI", FakeOpenAI)

    runtime = OpenAIImageRuntime(
        output_dir=tmp_path,
        api_key="test-key",
        base_url="https://geekspace.cloud/v1",
        image_model="gpt-image-2",
    )

    runtime._build_client()

    assert captured["api_key"] == "test-key"
    assert captured["base_url"] == "https://geekspace.cloud/v1"
    assert captured["max_retries"] == 0
    assert captured["trust_env"] is False
    assert captured["timeout"] == 300
    assert "http_client" in captured
