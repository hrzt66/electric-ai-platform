# Electric AI Platform Final Design

> Version: v1.0
> Updated: 2026-04-08
> Note: This document consolidates the previous platform specs, runtime migration notes, scoring-model design, UI/UX redesign docs, and mobile/web-console design iterations into a single final design document.

## 1. Project Positioning

Electric AI Platform is a graduation-project-oriented but engineering-driven system for power-industry image generation and multidimensional quality evaluation. The platform is not limited to a one-off image generation demo. It aims to provide a complete product loop across generation, scoring, history review, audit tracking, model management, and deployment.

The final system should support:

- realistic power-scene image generation
- four-dimension image quality scoring
- model and prompt template management
- task orchestration and audit visibility
- history review and result comparison
- Windows-native and Docker deployment paths

## 2. Final Scope

### 2.1 In Scope

- Go microservice backend with clear domain boundaries
- Python runtime for real generation and real scoring
- Vue 3 web console with desktop and mobile support
- model registry, task center, asset center, audit center
- history pagination, score display, result preview, audit readability
- specialized electric-domain generation and scoring model evolution path

### 2.2 Out of Scope

- Kubernetes and multi-node production orchestration
- object storage replacement as a hard requirement for v1
- fully automated external alert channels
- separate mobile app or dedicated mobile-only frontend

## 3. Architecture Overview

### 3.1 Technology Stack

- Frontend: `Vue 3`, `TypeScript`, `Vite`, `Pinia`, `Vue Router`, `Element Plus`
- Backend: `Go 1.24`, `Gin`
- AI Runtime: `Python 3.10`, `FastAPI`, `PyTorch`, `diffusers`, `transformers`
- Database: `MySQL 8`
- Queue and cache: `Redis 7`
- Deployment: `Windows native scripts` and `Docker Compose`

### 3.2 System Topology

```text
Web Console
    |
    v
Gateway Service
    |
    +----------+-----------+-----------+-----------+-----------+
    |          |           |           |           |           |
    v          v           v           v           v           v
 Auth      Model        Task        Asset       Audit      Runtime Status
 Service   Service      Service     Service     Service    (logical)
                          |
                          v
                        Redis Streams
                          |
                          v
                   Python AI Runtime
                          |
            +-------------+-------------+
            |                           |
            v                           v
   Generation Runtime             Scoring Runtime
```

### 3.3 Core Design Principles

- Keep Go microservice boundaries stable instead of collapsing back to a monolith.
- Centralize all heavy AI execution in Python runtime to isolate deep-learning dependencies.
- Treat generation, scoring, export, and comparison as task-driven workflows.
- Preserve a unified design language across login, workbench, history, audit, and mobile views.
- Favor deployable and demo-ready solutions over oversized architecture.

## 4. Domain Service Design

### 4.1 Gateway Service

- unified API entry
- token verification and user context forwarding
- request logging, rate limiting, CORS, and response shaping
- static image access and cross-service gateway routing

### 4.2 Auth Service

- login and token issuing
- refresh-token flow
- user identity and basic permission checks
- login audit records

### 4.3 Model Service

- generation-model registry
- scoring-model registry
- prompt templates and default presets
- runtime capability and availability status

### 4.4 Task Service

- job creation and lifecycle tracking
- Redis Stream publish flow
- generate and score chaining
- retry, timeout, and cancel support

### 4.5 Asset Service

- generated image persistence
- prompt and score result persistence
- history list and history detail aggregation
- paginated querying with filters

### 4.6 Audit Service

- task-event recording
- readable audit timeline data source
- operation trace and export audit basis

### 4.7 Python AI Runtime

- model loading and unloading
- generation execution
- multidimensional scoring execution
- explicit VRAM cleanup
- task status callback and failure summary reporting

## 5. Data and Storage Design

### 5.1 Existing Schema Basis

The current project started from a minimal `DB.sql` with:

- `ai_models`
- `images`
- `image_prompts`

This is enough for an early demo, but not enough for a real platform loop.

### 5.2 Final Recommended Data Domains

- `auth_*`: users, roles, permissions, refresh tokens, login logs
- `model_*`: registry, versions, prompt templates, score profiles, power keywords
- `task_*`: jobs, job steps, retry logs, experiment roots, experiment items
- `asset_*`: images, prompts, scores, files, tags
- `audit_*`: operation logs, API logs, task events, alerts, export records

### 5.3 Storage Strategy

- MySQL stores structured business records.
- Redis stores task queues, cache entries, and lightweight coordination state.
- generated files are stored under runtime-controlled local directories
- deployed runtime root is centered around `G:\electric-ai-runtime`

## 6. Legacy Capability Migration Strategy

The final platform is not a greenfield design anymore. It evolves from a previous system that already had real model and frontend capabilities. The migration strategy is:

1. Keep the new Go microservice structure.
2. Move real generation and real scoring into `python-ai-service`.
3. Rebuild the old frontend capabilities inside the new `web-console`.
4. Persist images, prompts, scores, and task status through the new service boundaries.
5. Preserve Windows-native operation as a first-class runtime path.

This migration is important because the final platform must be more than a mocked vertical slice.

## 7. Generation Design

### 7.1 Runtime Direction

The final deployed generation direction remains `Stable Diffusion 1.5` based for one practical reason: the target machine is a Windows laptop environment with `RTX 3060 Laptop GPU 6GB`, so deployment stability matters more than chasing larger base models.

### 7.2 Specialized Electric Model

The final model strategy is:

- build an electric-domain dataset from public and local power-scene images
- fine-tune an SD1.5-based electric LoRA
- merge the LoRA into a standalone deployable runtime model
- register it as `sd15-electric-specialized`

This approach balances:

- electric-domain specificity
- trainability on limited hardware
- deploy-time stability
- compatibility with existing runtime code

### 7.3 Prompt-Library Design

Prompt design follows a reusable layered pattern:

- realism backbone
- scene template
- environment modifiers
- camera and light modifiers
- negative prompt constraints

Representative scene families:

- substation close-up
- transmission-line aerial view
- grid control room
- wind farm
- solar farm
- hydro dam
- night maintenance

Prompt goals:

- realistic materials and equipment structure
- clean industrial composition
- safety cues and believable engineering layout
- reduced cartoon, CGI, and artifact drift

## 8. Scoring Design

### 8.1 Four Dimensions

The final scoring model evaluates:

- `text_consistency`
- `composition_aesthetics`
- `visual_fidelity`
- `physical_plausibility`

### 8.2 Scoring Runtime Structure

The platform keeps a layered scorer:

- advanced scorers first:
  - `ImageReward`
  - `LAION-Aesthetics`
  - `CLIP-IQA`
- fallback scorer:
  - pure `CLIP-IQA` flow

This provides:

- stronger human-aligned evaluation when advanced models are available
- predictable fallback behavior when heavyweight models fail to load
- better demo stability on limited hardware

### 8.3 Electric Score V3 Direction

The final scoring evolution path is `electric-score-v3`, which combines:

- teacher-model supervision for human-aligned quality signals
- electric-component detection and rule constraints
- lightweight student inference for deploy-time scoring

This means the platform does not rely only on generic aesthetic scoring. It also keeps domain-specific checks for:

- power-component presence
- structural plausibility
- cable behavior and equipment relationships
- electric-scene physical logic

### 8.4 Final Total-Score Strategy

Recommended default total score:

```text
total_score =
  visual_fidelity * 0.25 +
  text_consistency * 0.30 +
  physical_plausibility * 0.30 +
  composition_aesthetics * 0.15
```

## 9. Task and Workflow Design

### 9.1 Generate Workflow

1. user submits prompt and runtime parameters from the workbench
2. `task-service` creates a generate job
3. job is published to Redis Stream
4. Python runtime consumes the job and runs generation
5. asset metadata is persisted
6. audit events are written
7. a follow-up score job is created automatically

### 9.2 Score Workflow

1. `task-service` creates a scoring job
2. Python runtime runs the four-dimension scorer
3. results are written to asset records
4. score summaries and audit events become visible in the console

### 9.3 History Workflow

The final history center design includes:

- real backend pagination
- filter state reflected into query parameters
- unchanged detail-drawer flow for record drill-down
- reusable list-loading path instead of full eager history fetches

This keeps the history page scalable as data volume grows.

## 10. Final Web Console Design

### 10.1 Login Experience

The login page is finalized as an industrial control center style entrance:

- left-side narrative zone for platform identity
- right-side login cabin for the only entry point
- deep blue steel background with copper-gold accents
- platform-oriented wording instead of a generic admin login look

### 10.2 Generation Workbench

The workbench remains the main operator page and must present:

- model selection and prompt controls
- task state feedback
- score panel and radar summary
- result preview with stable layout

A key final UX decision is the fixed preview frame:

- generated images stay inside the preview card
- the central column no longer gets visually flooded by full-height images
- users can still click to open a larger preview overlay

### 10.3 Score Readability

Score presentation is finalized with:

- numeric score values
- grade badges for the four dimensions only
- quick visual differentiation of weak and strong results

Recommended mapping:

- `0-30`: `E`
- `30-50`: `D`
- `50-70`: `C`
- `70-85`: `B`
- `85-100`: `A`

### 10.4 Audit Readability

Audit presentation is finalized around a shared readable timeline approach:

- raw event names are mapped to readable Chinese titles
- payload summaries are converted into Chinese descriptions
- the same presentation logic is reused in generate, audit, and history detail surfaces

This avoids the old “English event name + raw JSON dump” problem.

### 10.5 Mobile Design

The final mobile design is a two-step result:

1. make every page actually usable on phones
2. reduce visual heaviness so the phone UI feels like a light native console instead of compressed desktop cards

The final mobile direction includes:

- drawer-based secondary navigation
- bottom navigation for major page switching
- single-column mobile layouts
- thinner cards and shorter modules
- reduced chrome height
- more useful first-screen density

### 10.6 Responsive Principles

- desktop structure stays recognizable
- no separate mobile site or route tree
- functionality is preserved, not removed
- layout changes are mostly done through responsive branches and scoped styling

## 11. Deployment and Runtime Design

### 11.1 Windows Native Path

Windows native operation remains a first-class deployment target because it is the main demo and development environment. The runtime should keep:

- Python environment under `G:\miniconda3\envs\electric-ai-py310`
- model and output storage under `G:\electric-ai-runtime`
- service ports aligned with the current local workflow

### 11.2 Docker Path

Docker Compose remains the secondary standardized deployment path for:

- reproducible environment startup
- demo environment packaging
- service orchestration consistency

## 12. Testing and Verification Strategy

### 12.1 Backend

- service-level unit tests
- repository tests
- pagination and filter behavior tests
- task lifecycle tests

### 12.2 Frontend

- source-content and logic tests for responsive branches
- focused component tests for result preview, score badges, and history detail
- store tests for pagination and query-state behavior

### 12.3 Runtime

- real generation smoke tests
- real scoring smoke tests
- model availability checks
- deployment-path verification for specialized models

## 13. Final Deliverable Summary

The final design is not just “platform architecture” anymore. It is the combined result of:

- the original platform blueprint
- the real-runtime migration plan
- the specialized electric model strategy
- the upgraded human-aligned scoring design
- the web-console desktop polish
- the mobile responsive and density refinements
- the history center scalability upgrades

## 14. Conclusion

This final design document serves as the single source of truth for Electric AI Platform.

It unifies:

- system architecture
- runtime strategy
- data boundaries
- generation and scoring design
- final web-console interaction model
- deployment and verification direction

All previous intermediate spec and plan markdown files are superseded by this document and removed from `docs/superpowers`.
