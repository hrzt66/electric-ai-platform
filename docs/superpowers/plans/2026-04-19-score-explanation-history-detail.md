# Score Explanation History Detail Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist per-image score explanations, expose them through the asset detail API, and let the history center open a detailed explanation modal for each score dimension including YOLO checked images when available.

**Architecture:** Extend the Python scoring runtime so each scored image returns a structured explanation payload beside the numeric scores. Persist that payload in a new asset-service table keyed by image, expose it from the existing detail endpoint, add a second gateway static route for `model/image_check`, and update the history drawer so each score chip opens a modal that renders either YOLO evidence or formula-based reasoning.

**Tech Stack:** Python FastAPI runtime, Go asset-service and gateway-service, MySQL schema bootstrap, Vue 3 + Element Plus, Vitest, pytest, Go test.

---

### Task 1: Add Explanation Contract Tests

**Files:**
- Modify: `python-ai-service/tests/test_power_score_runtime.py`
- Modify: `python-ai-service/tests/test_scoring_service.py`
- Modify: `services/asset-service/service/asset_service_test.go`
- Modify: `web-console/src/components/history/history-detail-drawer.spec.ts`
- Modify: `services/gateway-service/service/proxy_service_test.go`

- [ ] Write failing tests for explanation generation, persistence, checked-image URL handling, and modal rendering.
- [ ] Run focused pytest, Go test, and Vitest commands to verify the failures are on the missing explanation contract.

### Task 2: Persist Explanation Data End-to-End

**Files:**
- Modify: `deploy/mysql/init/001_schema.sql`
- Modify: `services/asset-service/model/asset.go`
- Modify: `services/asset-service/repository/asset_repository.go`
- Modify: `services/asset-service/service/asset_service.go`
- Modify: `python-ai-service/app/runtimes/scorers/power_score_runtime.py`
- Modify: `python-ai-service/app/services/scoring_service.py`

- [ ] Add a dedicated explanation table with one row per image.
- [ ] Extend Python scoring output to include structured explanations and checked image path.
- [ ] Save and load explanations in asset-service without breaking older rows that lack explanation data.

### Task 3: Expose Checked Images and History Detail UI

**Files:**
- Modify: `services/gateway-service/cmd/server/main.go`
- Modify: `services/gateway-service/router/router.go`
- Modify: `web-console/src/types/platform.ts`
- Modify: `web-console/src/api/platform.ts`
- Modify: `web-console/src/components/history/HistoryDetailDrawer.vue`

- [ ] Add a gateway file route for `model/image_check`.
- [ ] Extend frontend types and URL helpers for original and checked images.
- [ ] Make score chips clickable and render a detailed modal with YOLO evidence, formulas, and saved explanations.

### Task 4: Verify the Full Slice

**Files:**
- Modify only if verification uncovers bugs in the files above.

- [ ] Run focused verification for Python, Go, and frontend.
- [ ] Check that old detail records still render safely when explanation data is absent.
