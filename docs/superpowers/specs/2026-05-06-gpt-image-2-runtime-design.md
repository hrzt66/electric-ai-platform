# GPT Image 2 Runtime Design

## Goal

Add `gpt-image-2` as an optional generation model in the existing Electric AI Platform without replacing the current local generation runtimes and without modifying `/Users/hrzt/code/vibe coding/codex/毕业设计/image`.

## Context

The standalone image implementation in `/Users/hrzt/code/vibe coding/codex/毕业设计/image/generate_image.py` proves the API behavior:

- It calls an OpenAI-compatible Images API through the `openai` Python SDK.
- It defaults to `OPENAI_BASE_URL` or `https://geekspace.cloud/v1`.
- It defaults to `OPENAI_IMAGE_MODEL` or `gpt-image-2`.
- `gpt-image-*` responses are expected as Base64 image data.
- URL responses are still useful to support DALL-E style fallback behavior.

The platform already routes generation through `python-ai-service/app/runtimes/runtime_registry.py`. Each generation runtime implements `generate(...)`, writes images into `Settings.output_image_dir`, and returns records containing `file_path`, `seed`, `width`, `height`, and `model_name`.

## Recommended Approach

Add a new `OpenAIImageRuntime` to `python-ai-service` and register it under the model name `gpt-image-2`.

This keeps the existing task flow intact:

1. The UI submits a normal generation task with `model_name: "gpt-image-2"`.
2. The worker or FastAPI internal endpoint asks `RuntimeRegistry` for that runtime.
3. `GenerationService` resolves the seed and calls `runtime.generate(...)`.
4. The runtime calls the OpenAI-compatible Images API, saves the returned image locally, and returns normal generated image records.
5. The existing scoring, asset, task, and audit flow can continue without needing a separate endpoint.

## Runtime Behavior

`OpenAIImageRuntime` should:

- Accept `output_dir`, `api_key`, `base_url`, `image_model`, and optional SDK client injection for tests.
- Read credentials from environment through settings or helper functions, not from the standalone script.
- Refuse to run with a missing API key and raise a clear runtime error.
- Build the requested size as `"{width}x{height}"`.
- Validate sizes only when the resolved image model is `dall-e-2`; supported DALL-E 2 sizes are `256x256`, `512x512`, and `1024x1024`.
- For `gpt-image-*`, call `client.images.generate(...)` without `response_format`; the expected response contains `b64_json`.
- For URL-style models, pass `response_format="url"` and download the returned URL.
- Save PNG files under `Settings.output_image_dir` using the existing platform naming style, such as `{job_id}_{index}_{seed}.png`.
- Return one record per generated image with the platform's existing generated-image fields.

The runtime should preserve the platform-level seed field in returned records even though the external API may not be deterministic from that seed.

## Model Registry And Manifest

Register `gpt-image-2` in:

- `python-ai-service/app/runtimes/runtime_registry.py`
- `python-ai-service/scripts/download_models.py`
- `deploy/mysql/init/002_seed.sql`
- `web-console/src/model-copy.ts`

Manifest status should not depend on a local model directory for `gpt-image-2`. It should be treated as available when the runtime is registered, because it is an API-backed model rather than a local checkpoint.

The model copy should make clear that it is an OpenAI-compatible Image 2 API runtime for high-quality electric scene generation.

## Configuration

Add environment-backed configuration to `python-ai-service/app/core/settings.py`:

- `OPENAI_API_KEY`
- `OPENAI_BASE_URL`, default `https://geekspace.cloud/v1`
- `OPENAI_IMAGE_MODEL`, default `gpt-image-2`

The project should not copy the hard-coded API key from the standalone script. Runtime deployment must provide the key through environment variables or `.env.local`.

## Dependencies

Add these Python dependencies to `python-ai-service/requirements.txt`:

- `openai>=1.0.0`
- `requests>=2.31.0`

`requests` is needed only for URL response download compatibility.

## Error Handling

The runtime should convert common failures into readable `RuntimeError` messages:

- Missing `openai` dependency.
- Missing API key.
- API authentication failure.
- API connection failure.
- Unsupported DALL-E 2 size.
- Missing image data in the API response.
- Base64 decode failure.
- URL download failure.

The existing job pipeline can then mark the task as failed using its current error propagation behavior.

## Testing

Add focused tests that do not call the real API:

- `OpenAIImageRuntime` saves Base64 image data into `output_dir` and returns the expected generated image record.
- `OpenAIImageRuntime` downloads URL image data through an injected downloader and returns the expected record.
- `OpenAIImageRuntime` rejects unsupported DALL-E 2 sizes.
- `RuntimeRegistry` builds an `OpenAIImageRuntime` for `gpt-image-2`.
- `RuntimeRegistry.list_models()` reports `gpt-image-2` as available.
- The model manifest includes `gpt-image-2` as a generation runtime.

Run the Python test subset before completion:

```bash
cd python-ai-service
pytest tests/test_openai_image_runtime.py tests/test_runtime_registry.py -q
```

If frontend copy changes are made, also run the related web tests:

```bash
cd web-console
npm test -- model-copy
```

## Out Of Scope

- Do not modify `/Users/hrzt/code/vibe coding/codex/毕业设计/image`.
- Do not replace the default `ssd1b-electric` selection unless requested separately.
- Do not add a separate Image 2-only API endpoint.
- Do not implement real external API integration tests that require a live key.
