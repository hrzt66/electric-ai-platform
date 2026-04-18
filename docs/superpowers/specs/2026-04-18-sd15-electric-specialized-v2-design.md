# SD15 Electric Specialized V2 Design

**Date:** 2026-04-18

**Goal**

Build a new electric-domain specialized Stable Diffusion 1.5 model for realistic utility inspection and industrial photography scenes. The pipeline must automatically download a legally usable public image dataset, clean and caption it, train a 100-epoch LoRA on top of SD1.5, merge the best checkpoint into a standalone deployment model, and replace the previous `sd15-electric-specialized` artifacts.

## Scope

This design covers:

- Public dataset acquisition from official/open APIs
- Dataset licensing filters, dedupe, caption normalization, and manifest generation
- SD1.5 LoRA training configured for 100 epochs on Apple Silicon
- Best-checkpoint selection, LoRA merge, evaluation, and deployment
- Cleanup of the previous `sd15-electric-specialized` training and deployment artifacts

This design does not cover:

- Training a new base model from scratch
- Adding non-SD1.5 generation families
- Building a new labeling UI or human review console

## User Intent

The target model should be:

- Electric-domain specific rather than generic industrial
- Focused on realistic inspection/documentary photography rather than poster art
- Broad enough to cover substations, transmission infrastructure, wind power, solar power, and field inspection scenes
- Delivered as a standalone merged model that can be used directly by the existing platform runtime

## Architecture

The implementation reuses the repository's existing SD1.5 generation training pipeline and extends it with a public-data ingestion stage. The end-to-end flow becomes:

1. Download public electric-domain images from approved sources into a raw dataset cache
2. Filter by license, image validity, and domain relevance
3. Dedupe files and build normalized captions/metadata manifests
4. Export a curated training dataset in the existing `metadata.jsonl` format
5. Train an SD1.5 LoRA for 100 epochs using MPS-safe settings
6. Evaluate checkpoints during training and select the best checkpoint
7. Merge the best checkpoint into a deployable `sd15-electric-specialized` model directory
8. Verify runtime loading and real task generation through the existing platform services

The final platform-facing model name stays `sd15-electric-specialized`. This preserves existing runtime wiring and avoids unnecessary front-end or catalog churn. Training artifacts for the new run are isolated under a `-v2` training workspace so the old model can be deleted while the new run remains traceable.

## Data Sources

### Approved Providers

The first implementation uses two providers:

- Openverse image search API
- Wikimedia Commons API

These providers were chosen because they have public documentation, usable metadata, and explicit license fields.

### Domain Buckets

The downloader must collect images into five conceptual buckets:

1. Substation and switchyard scenes
2. Transmission infrastructure and line inspection scenes
3. Wind power scenes
4. Solar power scenes
5. Utility inspection and industrial maintenance scenes

Each bucket uses a curated keyword list with English search terms such as:

- `substation`, `switchyard`, `transformer yard`, `switchgear`, `circuit breaker`
- `transmission tower`, `power line`, `insulator`, `utility pole`, `line inspection`
- `wind turbine`, `wind farm`
- `solar panel`, `solar farm`, `photovoltaic`, `inverter station`
- `utility inspection`, `industrial maintenance`, `power equipment`

### License Policy

Only images with one of these licenses are accepted:

- Public Domain
- CC0
- CC BY
- CC BY-SA

Images with `NC`, `ND`, unknown license, or missing source attribution are rejected.

For every accepted image, the pipeline stores:

- Provider name
- Source URL
- Original title/description when available
- Author/creator when available
- License identifier
- Attribution URL
- Search bucket and matched query

This metadata is persisted in an attribution manifest alongside the training dataset.

## Dataset Processing

### Raw Download Layout

Raw downloaded images are stored under:

- `model/datasets/generation-v3/raw/openverse/...`
- `model/datasets/generation-v3/raw/wikimedia/...`

Provider-specific JSON records are stored beside the images for traceability.

### Filtering

The ingestion stage must reject:

- Corrupted or zero-byte files
- Images below minimum size thresholds
- Images with unsupported suffixes
- License-ineligible images
- Exact duplicates by file fingerprint

Conservative relevance heuristics reject obviously irrelevant images by keyword mismatch after download.

### Target Dataset Size

Initial download target:

- 2,500 to 4,000 raw images total

Expected curated target after filtering and dedupe:

- 1,200 to 1,800 images

The downloader should balance buckets rather than allowing wind or solar content to dominate the final distribution.

### Caption Strategy

Captions should combine:

- Domain bucket label
- Search query intent
- Provider title/description if useful
- Normalized electric equipment phrases
- Fixed style prior favoring realistic utility photography

Example caption structure:

`realistic utility inspection photography, electric power substation, transformer equipment, outdoor industrial documentation photo`

This keeps the model aligned to electric-domain realism rather than generic landscape generation.

## Training Strategy

### Base Model

- `runwayml/stable-diffusion-v1-5`

If a local SD1.5 base model already exists in the runtime model directory, it can be used instead of pulling again from Hugging Face.

### Training Method

- SD1.5 LoRA training
- Best checkpoint merged into a standalone model directory

### Required Parameters

- Resolution: `512`
- Epochs: `100`
- Rank: `32`
- Alpha: `32`
- Train batch size: `1`
- Gradient accumulation steps: `8`
- Learning rate: `5e-5`
- LR scheduler: `cosine`
- Gradient checkpointing: `true`
- Validation images per checkpoint eval: small fixed set

### Apple Silicon / MPS Safety

Training defaults must be safe on the user's machine:

- Prefer `float32` / no mixed precision on MPS
- Enable `PYTORCH_ENABLE_MPS_FALLBACK=1`
- Keep batch size at `1`
- Preserve checkpoint resume capability

The design intentionally favors stability over maximum throughput.

### Epoch Policy

The run must complete 100 training epochs. However, deployment should merge the best validation checkpoint rather than blindly using the final epoch if validation indicates late overfitting. The run artifacts must still retain:

- Epoch-100 checkpoint/log state
- Validation images across the run
- Best checkpoint decision record

## Model Naming and Artifact Layout

### Final Deployment Name

Keep the platform-facing model name:

- `sd15-electric-specialized`

### New Training Workspace

Use a new isolated training root:

- `model/training/generation/sd15-electric-specialized-v2`

### Final Deployment Directory

Merged model is published to:

- `model/generation/sd15-electric-specialized`

### Dataset and Metadata Layout

- `model/datasets/generation-v3/raw/...`
- `model/datasets/generation-v3/manifests/raw_manifest.jsonl`
- `model/datasets/generation-v3/manifests/attribution_manifest.jsonl`
- `model/datasets/generation-v3/curated/...`

## Cleanup and Migration

Before training the new version, remove obsolete specialized artifacts if they exist:

- `model/training/generation/sd15-electric-specialized`
- `model/generation/sd15-electric-specialized`

The repository code should still expose `sd15-electric-specialized` as the final runtime model name, but the training pipeline internals move to the new `-v2` workspace.

## Validation and Acceptance

Acceptance is split into four layers.

### Data Layer

Must produce:

- Download report by provider and bucket
- Curated sample counts
- Dedupe summary
- Attribution/license manifest

### Training Layer

Must produce:

- 100-epoch training run
- Checkpoint directory
- Validation outputs
- Best-checkpoint selection record

### Model Layer

Must produce:

- Merged standalone model at `model/generation/sd15-electric-specialized`
- Loadable by the existing SD1.5 runtime

### Business Layer

Must verify:

- Model registry/catalog shows the specialized model as available
- A real generation task completes through the existing platform
- Output image is non-black and visually aligned with realistic electric-domain scenes

## Risks

### Risk: Domain Noise in Public Data

Public search results can include irrelevant infrastructure or artistic images. Mitigation:

- strict query lists
- license filtering
- keyword normalization
- bucket balancing
- optional conservative rejection heuristics

### Risk: Overfitting at 100 Epochs

100 epochs is intentionally aggressive for a curated electric dataset. Mitigation:

- validation monitoring
- best-checkpoint merge instead of always final checkpoint

### Risk: MPS Instability

Apple Silicon MPS can fail or degrade with unsupported mixed precision settings. Mitigation:

- float32 defaults on MPS
- fallback environment variables
- low-memory settings and checkpoint resume

## Success Criteria

The design is successful when:

- The platform can build its own electric-domain public dataset without requiring a manual training set
- The training pipeline completes a 100-epoch SD1.5 LoRA run
- The final merged `sd15-electric-specialized` model replaces the old specialized model artifacts
- The model can generate realistic electric-industry images through the existing task flow
