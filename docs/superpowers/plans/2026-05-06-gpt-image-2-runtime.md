# GPT Image 2 Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `gpt-image-2` as an optional API-backed generation model in the existing Electric AI Platform.

**Architecture:** Implement a Python `OpenAIImageRuntime` that satisfies the existing generation runtime protocol and register it in `RuntimeRegistry`. The runtime will save API-returned image bytes into the normal runtime image output directory, allowing current scoring, asset, task, and audit flows to stay unchanged.

**Tech Stack:** Python 3, FastAPI service runtime, OpenAI Python SDK, requests, pytest, Vue/Vitest model copy tests, MySQL seed SQL.

---

## File Structure

- Create `python-ai-service/app/runtimes/openai_image_runtime.py`: API-backed generation runtime, response extraction, Base64 save, URL download, DALL-E 2 size validation.
- Create `python-ai-service/tests/test_openai_image_runtime.py`: isolated runtime tests with fake SDK clients and fake downloaders.
- Modify `python-ai-service/app/core/settings.py`: add OpenAI image API environment settings.
- Modify `python-ai-service/app/runtimes/runtime_registry.py`: register and build `gpt-image-2`; mark remote API runtime available.
- Modify `python-ai-service/scripts/download_models.py`: add manifest entry for `gpt-image-2`.
- Modify `python-ai-service/tests/test_runtime_registry.py`: cover runtime construction and available manifest status.
- Modify `python-ai-service/requirements.txt`: add `openai` and `requests`.
- Modify `deploy/mysql/init/002_seed.sql`: seed `gpt-image-2` as a generation model.
- Modify `web-console/src/model-copy.ts`: add localized copy for `gpt-image-2`.
- Modify `web-console/src/model-copy.spec.ts`: test localized Image 2 display copy.

## Task 1: OpenAI Image Runtime Unit Tests

**Files:**
- Create: `python-ai-service/tests/test_openai_image_runtime.py`

- [ ] **Step 1: Write failing tests**

Create `python-ai-service/tests/test_openai_image_runtime.py` with:

```python
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
        return self.response


class FakeOpenAIClient:
    def __init__(self, response) -> None:
        self.images = FakeImagesClient(response)


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
            "size": "512x512",
            "n": 1,
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
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd python-ai-service
pytest tests/test_openai_image_runtime.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'app.runtimes.openai_image_runtime'`.

## Task 2: Implement OpenAI Image Runtime

**Files:**
- Create: `python-ai-service/app/runtimes/openai_image_runtime.py`
- Modify: `python-ai-service/requirements.txt`

- [ ] **Step 1: Add dependencies**

Append these lines to `python-ai-service/requirements.txt`:

```text
openai>=1.0.0
requests>=2.31.0
```

- [ ] **Step 2: Implement runtime**

Create `python-ai-service/app/runtimes/openai_image_runtime.py`:

```python
from __future__ import annotations

"""OpenAI-compatible Images API generation runtime."""

import base64
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

from app.runtimes.base import GeneratedImageRecord

SUPPORTED_DALLE2_SIZES = {"256x256", "512x512", "1024x1024"}


class OpenAIImageRuntime:
    """Generate images through an OpenAI-compatible Images API."""

    def __init__(
        self,
        *,
        output_dir: Path,
        api_key: str | None,
        base_url: str | None,
        image_model: str,
        client_factory: Callable[..., Any] | None = None,
        url_downloader: Callable[[str], bytes] | None = None,
    ) -> None:
        self.output_dir = Path(output_dir)
        self.api_key = api_key
        self.base_url = base_url.rstrip("/") if base_url else None
        self.image_model = image_model
        self._client_factory = client_factory
        self._url_downloader = url_downloader or self._download_url

    def prepare(self, job=None) -> None:
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is required to use gpt-image-2.")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(
        self,
        *,
        job_id: int,
        prompt: str,
        negative_prompt: str,
        seed: int,
        width: int,
        height: int,
        steps: int,
        guidance_scale: float,
        num_images: int,
        model_name: str,
    ) -> list[dict]:
        self.prepare()
        client = self._build_client()
        size = self._validate_size(f"{width}x{height}")
        request_kwargs: dict[str, Any] = {
            "model": self.image_model,
            "prompt": prompt,
            "size": size,
            "n": num_images,
        }
        if self._uses_url_response:
            request_kwargs["response_format"] = "url"

        response = client.images.generate(**request_kwargs)
        payloads = self._extract_payloads(response)

        saved: list[dict] = []
        for index, payload in enumerate(payloads):
            image_path = self.output_dir / f"{job_id}_{index}_{seed}.png"
            image_path.write_bytes(payload)
            saved.append(
                asdict(
                    GeneratedImageRecord(
                        file_path=str(image_path),
                        seed=seed,
                        width=width,
                        height=height,
                        model_name=model_name,
                    )
                )
            )
        return saved

    @property
    def _uses_url_response(self) -> bool:
        return not self.image_model.startswith("gpt-image-")

    def _build_client(self):
        if self._client_factory is not None:
            return self._client_factory(api_key=self.api_key, base_url=self.base_url)

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("Missing openai dependency. Install openai>=1.0.0.") from exc

        return OpenAI(api_key=self.api_key, base_url=self.base_url, max_retries=0)

    def _validate_size(self, size: str) -> str:
        if self.image_model != "dall-e-2":
            return size
        if size not in SUPPORTED_DALLE2_SIZES:
            supported = ", ".join(sorted(SUPPORTED_DALLE2_SIZES))
            raise ValueError(f"Unsupported DALL-E 2 image size: {size}. Supported sizes: {supported}.")
        return size

    def _extract_payloads(self, response: object) -> list[bytes]:
        data = self._get_data_items(response)
        payloads: list[bytes] = []
        for item in data:
            b64_json = self._get_value(item, "b64_json")
            if b64_json:
                payloads.append(self._decode_base64(b64_json))
                continue

            image_url = self._get_value(item, "url")
            if image_url:
                payloads.append(self._url_downloader(str(image_url)))
                continue

            raise RuntimeError("OpenAI image response item did not contain b64_json or url.")

        if not payloads:
            raise RuntimeError("OpenAI image response did not contain image data.")
        return payloads

    def _get_data_items(self, response: object) -> list[object]:
        if isinstance(response, dict):
            data = response.get("data")
        else:
            data = getattr(response, "data", None)
        if not isinstance(data, list):
            raise RuntimeError("OpenAI image response did not contain a data list.")
        return data

    def _get_value(self, item: object, key: str) -> object | None:
        if isinstance(item, dict):
            return item.get(key)
        return getattr(item, key, None)

    def _decode_base64(self, value: object) -> bytes:
        try:
            return base64.b64decode(str(value))
        except ValueError as exc:
            raise RuntimeError("OpenAI image response contained invalid Base64 data.") from exc

    def _download_url(self, image_url: str) -> bytes:
        parsed_url = urlparse(image_url)
        if parsed_url.scheme not in {"http", "https"}:
            raise ValueError(f"Invalid image URL: {image_url}")

        try:
            import requests
        except ImportError as exc:
            raise RuntimeError("Missing requests dependency. Install requests>=2.31.0.") from exc

        response = requests.get(image_url, timeout=60)
        try:
            response.raise_for_status()
        except requests.RequestException as exc:
            raise RuntimeError(f"Image download failed with HTTP status {response.status_code}.") from exc
        return response.content
```

- [ ] **Step 3: Run runtime tests**

Run:

```bash
cd python-ai-service
pytest tests/test_openai_image_runtime.py -q
```

Expected: PASS.

## Task 3: Settings And Registry Integration

**Files:**
- Modify: `python-ai-service/app/core/settings.py`
- Modify: `python-ai-service/app/runtimes/runtime_registry.py`
- Modify: `python-ai-service/scripts/download_models.py`
- Modify: `python-ai-service/tests/test_runtime_registry.py`

- [ ] **Step 1: Add failing registry tests**

Append to `python-ai-service/tests/test_runtime_registry.py`:

```python
def test_runtime_registry_builds_gpt_image2_runtime_from_settings(tmp_path):
    from app.core.settings import Settings
    from app.runtimes.openai_image_runtime import OpenAIImageRuntime
    from app.runtimes.runtime_registry import RuntimeRegistry

    settings = Settings(
        runtime_root=tmp_path,
        openai_api_key="test-key",
        openai_base_url="https://geekspace.cloud/v1",
        openai_image_model="gpt-image-2",
    )
    registry = RuntimeRegistry(settings=settings)

    runtime = registry.get_generation_runtime("gpt-image-2")

    assert isinstance(runtime, OpenAIImageRuntime)
    assert runtime.output_dir == tmp_path / "image"
    assert runtime.image_model == "gpt-image-2"


def test_runtime_registry_lists_gpt_image2_as_available_api_runtime(tmp_path):
    from app.core.settings import Settings
    from app.runtimes.runtime_registry import RuntimeRegistry

    settings = Settings(runtime_root=tmp_path)
    registry = RuntimeRegistry(settings=settings)

    items = registry.list_models()["items"]
    image2 = next(item for item in items if item["name"] == "gpt-image-2")

    assert image2["status"] == "available"
    assert image2["ready"] is True
    assert image2["source"] == "api-runtime"
```

- [ ] **Step 2: Run registry tests to verify failure**

Run:

```bash
cd python-ai-service
pytest tests/test_runtime_registry.py::test_runtime_registry_builds_gpt_image2_runtime_from_settings tests/test_runtime_registry.py::test_runtime_registry_lists_gpt_image2_as_available_api_runtime -q
```

Expected: FAIL because `Settings` has no OpenAI fields and `gpt-image-2` is not registered.

- [ ] **Step 3: Add settings fields**

In `python-ai-service/app/core/settings.py`, add fields to `Settings`:

```python
    openai_api_key: str | None = None
    openai_base_url: str = "https://geekspace.cloud/v1"
    openai_image_model: str = "gpt-image-2"
```

In `Settings.from_env`, add constructor arguments:

```python
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_base_url=os.getenv("OPENAI_BASE_URL", "https://geekspace.cloud/v1"),
            openai_image_model=os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-2"),
```

- [ ] **Step 4: Add manifest entry**

In `python-ai-service/scripts/download_models.py`, add this entry inside `manifest` after the other generation models:

```python
        "gpt-image-2": RuntimeModelManifestEntry(
            name="gpt-image-2",
            target="generation",
            source="api-runtime",
            local_dir=str(paths.models_generation / "gpt-image-2"),
            description="OpenAI-compatible Image 2 API generation runtime",
        ),
```

- [ ] **Step 5: Allow api-runtime source type**

In `python-ai-service/app/schemas/runtime.py`, update `RuntimeModelManifestEntry.source` to:

```python
    source: Literal["huggingface", "local-copy", "local-runtime", "api-runtime"]
```

- [ ] **Step 6: Register runtime factory**

In `python-ai-service/app/runtimes/runtime_registry.py`, import the runtime:

```python
from app.runtimes.openai_image_runtime import OpenAIImageRuntime
```

Add factory:

```python
            "gpt-image-2": self._build_openai_image_runtime,
```

Add builder method:

```python
    def _build_openai_image_runtime(self) -> OpenAIImageRuntime:
        """构造 OpenAI 兼容 Image 2 API 运行时实例。"""
        return OpenAIImageRuntime(
            output_dir=self._settings.output_image_dir,
            api_key=self._settings.openai_api_key,
            base_url=self._settings.openai_base_url,
            image_model=self._settings.openai_image_model,
        )
```

- [ ] **Step 7: Mark api-runtime available**

In `RuntimeRegistry.list_models`, compute readiness as:

```python
            is_api_runtime = entry["source"] == "api-runtime"
            has_files = local_dir.exists() and any(local_dir.iterdir())
```

Then set:

```python
                    "status": self._resolve_status(
                        name=name,
                        target=entry["target"],
                        source=entry["source"],
                        has_files=has_files,
                    ),
                    "ready": is_api_runtime or has_files,
```

Update `_resolve_status` signature and body:

```python
    def _resolve_status(self, *, name: str, target: str, source: str, has_files: bool) -> str:
        """根据本地目录内容和模型目标类型推导最终展示状态。"""
        if source == "api-runtime":
            return "available" if name in self._generation_runtime_factories else "experimental"
        if has_files:
            return "available"
        if target == "generation" and name not in self._generation_runtime_factories:
            return "experimental"
        return "unavailable"
```

- [ ] **Step 8: Run registry tests**

Run:

```bash
cd python-ai-service
pytest tests/test_runtime_registry.py -q
```

Expected: PASS.

## Task 4: Seed Data And Frontend Copy

**Files:**
- Modify: `deploy/mysql/init/002_seed.sql`
- Modify: `web-console/src/model-copy.ts`
- Modify: `web-console/src/model-copy.spec.ts`

- [ ] **Step 1: Add failing frontend copy test**

Append to `web-console/src/model-copy.spec.ts`:

```typescript
  it('localizes gpt-image-2 as an API generation model', () => {
    const localized = localizeModelRecord(
      buildModelRecord({
        model_name: 'gpt-image-2',
        display_name: 'GPT Image 2',
        description: 'OpenAI-compatible Image 2 API generation runtime',
        local_path: 'api/openai/gpt-image-2',
      }),
    )

    expect(localized.display_name).toBe('GPT Image 2 电力云生图')
    expect(localized.description).toContain('OpenAI 兼容')
  })
```

- [ ] **Step 2: Run frontend test to verify failure**

Run:

```bash
cd web-console
npm test -- model-copy
```

Expected: FAIL because `gpt-image-2` is not localized yet.

- [ ] **Step 3: Add localized model copy**

In `web-console/src/model-copy.ts`, add:

```typescript
  'gpt-image-2': {
    display_name: 'GPT Image 2 电力云生图',
    description: '通过 OpenAI 兼容 Image 2 API 生成高质量电力场景图片，适合不依赖本地显卡的云端出图。',
  },
```

- [ ] **Step 4: Add SQL seed row**

In `deploy/mysql/init/002_seed.sql`, add this row after `unipic2-kontext`:

```sql
('gpt-image-2', 'GPT Image 2', 'generation', 'python-ai-service', 'available', 'OpenAI-compatible Image 2 API generation runtime', '500kV substation, industrial realism, detailed power equipment, high quality', 'blurry, low quality, artifact, deformed geometry', 'api/openai/gpt-image-2'),
```

- [ ] **Step 5: Run frontend copy test**

Run:

```bash
cd web-console
npm test -- model-copy
```

Expected: PASS.

## Task 5: Final Verification

**Files:**
- Verify only.

- [ ] **Step 1: Run Python focused tests**

Run:

```bash
cd python-ai-service
pytest tests/test_openai_image_runtime.py tests/test_runtime_registry.py -q
```

Expected: PASS.

- [ ] **Step 2: Run manifest smoke check**

Run:

```bash
cd python-ai-service
python - <<'PY'
from scripts.download_models import get_model_manifest
entry = get_model_manifest()["gpt-image-2"]
print(entry["target"], entry["source"], entry["description"])
PY
```

Expected output contains:

```text
generation api-runtime OpenAI-compatible Image 2 API generation runtime
```

- [ ] **Step 3: Verify standalone image directory was not modified**

Run:

```bash
git -C "/Users/hrzt/code/vibe coding/codex/毕业设计/image" status --short
```

Expected: no changes caused by this implementation.

- [ ] **Step 4: Review changed files**

Run:

```bash
git diff -- python-ai-service/app/runtimes/openai_image_runtime.py python-ai-service/app/core/settings.py python-ai-service/app/runtimes/runtime_registry.py python-ai-service/scripts/download_models.py python-ai-service/app/schemas/runtime.py python-ai-service/tests/test_openai_image_runtime.py python-ai-service/tests/test_runtime_registry.py python-ai-service/requirements.txt deploy/mysql/init/002_seed.sql web-console/src/model-copy.ts web-console/src/model-copy.spec.ts docs/superpowers/specs/2026-05-06-gpt-image-2-runtime-design.md docs/superpowers/plans/2026-05-06-gpt-image-2-runtime.md
```

Expected: diff only includes the planned Image 2 integration and documentation changes.
