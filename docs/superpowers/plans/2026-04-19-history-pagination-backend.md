# History Pagination Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add backend-driven pagination and server-side filtering for the history center while preserving the existing non-paginated history API for other views.

**Architecture:** Keep `GET /api/v1/assets/history` unchanged for legacy consumers, and add a new `GET /api/v1/assets/history/page` endpoint in asset-service. The new endpoint will accept pagination and filter query params, run SQL filtering plus `LIMIT/OFFSET`, return `items/page/page_size/total/total_pages`, and the web console history view will switch to the paginated API and render Element Plus pagination controls.

**Tech Stack:** Go + Gin + database/sql in asset-service, Vue 3 + Pinia + Element Plus in web-console, Vitest, Go test.

---

### Task 1: Add Asset-Service Pagination Contract

**Files:**
- Modify: `services/asset-service/model/asset.go`
- Modify: `services/asset-service/service/asset_service.go`
- Modify: `services/asset-service/service/asset_service_test.go`

- [ ] **Step 1: Write the failing service test**

```go
func TestListHistoryPageReturnsPagedSliceAndTotals(t *testing.T) {
	repo := &memoryAssetRepo{
		records: []HistoryItem{
			{ID: 3, ImageName: "3.png", PositivePrompt: "tower", ModelName: "ssd1b-electric", Status: "scored", TotalScore: 78},
			{ID: 2, ImageName: "2.png", PositivePrompt: "substation", ModelName: "ssd1b-electric", Status: "scored", TotalScore: 65},
			{ID: 1, ImageName: "1.png", PositivePrompt: "dam", ModelName: "sd15-electric", Status: "generated", TotalScore: 41},
		},
	}
	svc := NewAssetService(repo)

	page, err := svc.ListHistoryPage(context.Background(), HistoryPageQuery{
		Page: 2,
		PageSize: 1,
		ModelName: "ssd1b-electric",
	})

	if err != nil {
		t.Fatalf("expected nil error, got %v", err)
	}
	if page.Total != 2 || page.TotalPages != 2 {
		t.Fatalf("unexpected totals: %+v", page)
	}
	if len(page.Items) != 1 || page.Items[0].ID != 2 {
		t.Fatalf("unexpected page items: %+v", page.Items)
	}
}
```

- [ ] **Step 2: Run the service test to verify it fails**

Run: `go test ./services/asset-service/service -run TestListHistoryPageReturnsPagedSliceAndTotals`
Expected: FAIL because `HistoryPageQuery`, `HistoryPageResult`, and `ListHistoryPage` do not exist yet.

- [ ] **Step 3: Add page/query types and service method**

```go
type HistoryPageQuery struct {
	Page          int    `form:"page"`
	PageSize      int    `form:"page_size"`
	PromptKeyword string `form:"prompt_keyword"`
	ModelName     string `form:"model_name"`
	Status        string `form:"status"`
	MinTotalScore int    `form:"min_total_score"`
}

type HistoryPageResult struct {
	Items      []HistoryItem `json:"items"`
	Page       int           `json:"page"`
	PageSize   int           `json:"page_size"`
	Total      int           `json:"total"`
	TotalPages int           `json:"total_pages"`
}
```

- [ ] **Step 4: Re-run the service test**

Run: `go test ./services/asset-service/service -run TestListHistoryPageReturnsPagedSliceAndTotals`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add services/asset-service/model/asset.go \
  services/asset-service/service/asset_service.go \
  services/asset-service/service/asset_service_test.go
git commit -m "feat: add asset-service history pagination types"
```

### Task 2: Add Repository SQL Pagination and HTTP Endpoint

**Files:**
- Modify: `services/asset-service/repository/asset_repository.go`
- Modify: `services/asset-service/controller/asset_controller.go`
- Modify: `services/asset-service/router/router.go`

- [ ] **Step 1: Write the failing repository/controller tests**

```go
func TestListHistoryPageBuildsFilteredResult(t *testing.T) {
	// insert three records, query prompt_keyword=substation page=1 page_size=1
	// expect total=2 and the newest matching row only
}
```

```go
func TestListHistoryPageRejectsInvalidPageParams(t *testing.T) {
	// GET /api/v1/assets/history/page?page=0&page_size=0
	// expect 400 with invalid pagination message
}
```

- [ ] **Step 2: Run the focused Go tests to verify they fail**

Run: `go test ./services/asset-service/...`
Expected: FAIL because paginated repository/controller behavior is not implemented.

- [ ] **Step 3: Implement SQL filtering, count query, and endpoint**

```go
func (r *AssetRepository) ListHistoryPage(ctx context.Context, query model.HistoryPageQuery) (model.HistoryPageResult, error) {
	whereSQL, args := buildHistoryWhereClause(query)
	countSQL := `SELECT COUNT(*) FROM ...` + whereSQL
	dataSQL := `SELECT ... FROM ...` + whereSQL + ` ORDER BY i.id DESC LIMIT ? OFFSET ?`
}
```

- [ ] **Step 4: Re-run the focused Go tests**

Run: `go test ./services/asset-service/...`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add services/asset-service/repository/asset_repository.go \
  services/asset-service/controller/asset_controller.go \
  services/asset-service/router/router.go
git commit -m "feat: add paged asset history endpoint"
```

### Task 3: Switch Web Console History View to Paged API

**Files:**
- Modify: `web-console/src/types/platform.ts`
- Modify: `web-console/src/api/platform.ts`
- Modify: `web-console/src/stores/platform.ts`
- Modify: `web-console/src/stores/platform.spec.ts`
- Modify: `web-console/src/views/HistoryView.vue`
- Modify: `web-console/src/components/history/HistoryTable.vue`

- [ ] **Step 1: Write the failing frontend tests**

```ts
it('fetches paged history with current filters and page args', async () => {
  api.listAssetHistoryPage.mockResolvedValue({
    items: [historyItem(12)],
    page: 2,
    page_size: 20,
    total: 42,
    total_pages: 3,
  })

  await store.fetchHistoryPage({
    page: 2,
    pageSize: 20,
    promptKeyword: 'tower',
    modelName: 'ssd1b-electric',
    status: 'scored',
    minTotalScore: 60,
  })

  expect(api.listAssetHistoryPage).toHaveBeenCalledWith({
    page: 2,
    page_size: 20,
    prompt_keyword: 'tower',
    model_name: 'ssd1b-electric',
    status: 'scored',
    min_total_score: 60,
  })
})
```

```ts
it('renders pagination from paged history result', async () => {
  const html = await renderHistoryView()
  expect(html).toContain('el-pagination')
})
```

- [ ] **Step 2: Run the focused frontend tests to verify they fail**

Run: `cd web-console && npm test -- --run src/stores/platform.spec.ts`
Expected: FAIL because paged history API/store state is missing.

- [ ] **Step 3: Implement paged history API, store state, and view wiring**

```ts
export type AssetHistoryPage = {
  items: AssetHistoryItem[]
  page: number
  page_size: number
  total: number
  total_pages: number
}
```

```ts
await listAssetHistoryPage({
  page,
  page_size: pageSize,
  prompt_keyword: promptKeyword,
  model_name: modelName,
  status,
  min_total_score: minTotalScore,
})
```

- [ ] **Step 4: Re-run the focused frontend tests**

Run: `cd web-console && npm test -- --run src/stores/platform.spec.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web-console/src/types/platform.ts \
  web-console/src/api/platform.ts \
  web-console/src/stores/platform.ts \
  web-console/src/stores/platform.spec.ts \
  web-console/src/views/HistoryView.vue \
  web-console/src/components/history/HistoryTable.vue
git commit -m "feat: paginate history center from backend"
```

### Task 4: Run Cross-Slice Verification

**Files:**
- Modify only if verification reveals issues in the files above.

- [ ] **Step 1: Run asset-service verification**

Run: `go test ./services/asset-service/...`
Expected: PASS.

- [ ] **Step 2: Run frontend verification**

Run: `cd web-console && npm test -- --run src/stores/platform.spec.ts src/components/history/history-detail-drawer.spec.ts`
Expected: PASS.

- [ ] **Step 3: Run a final focused integration sweep**

Run: `cd web-console && npm test -- --run src/api/platform.spec.ts`
Expected: PASS.
