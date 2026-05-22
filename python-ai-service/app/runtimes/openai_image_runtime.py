from __future__ import annotations

"""OpenAI-compatible Images API generation runtime."""

import base64
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

from httpx import Client as HttpxClient

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
        """Ensure runtime credentials and output directory are ready."""
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
        """Generate images with the configured Images API and save them locally."""
        self.prepare()
        client = self._build_client()
        size = self._resolve_size(width=width, height=height)
        request_kwargs: dict[str, Any] = {
            "model": self.image_model,
            "prompt": prompt,
            "size": size,
        }
        if self._uses_url_response:
            request_kwargs["n"] = num_images
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

        http_client = HttpxClient(trust_env=False, timeout=300)
        return OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            http_client=http_client,
            max_retries=0,
        )

    def _validate_size(self, size: str) -> str:
        if self.image_model != "dall-e-2":
            return size
        if size not in SUPPORTED_DALLE2_SIZES:
            supported = ", ".join(sorted(SUPPORTED_DALLE2_SIZES))
            raise ValueError(f"Unsupported DALL-E 2 image size: {size}. Supported sizes: {supported}.")
        return size

    def _resolve_size(self, *, width: int, height: int) -> str:
        if self.image_model.startswith("gpt-image-"):
            return "auto"
        return self._validate_size(f"{width}x{height}")

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
