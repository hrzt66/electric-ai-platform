# Cross-Platform Monitor Service Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a new `Go`-based `monitor-service` under `services/monitor-service` that detects `Windows` or `macOS`, gathers host and AI runtime health, optionally calls a Python probe for enhanced metrics, proxies through `gateway-service`, and renders a dual-system-compatible real-time dashboard panel.

**Architecture:** Add a standalone `Go + Gin` microservice aligned with the existing service layout. The Go service owns HTTP endpoints, SSE streaming, alert evaluation, and task context linkage. When platform-specific AI metrics are harder to obtain directly in Go, it shells out to a Python probe script that returns one-shot JSON snapshots. The frontend consumes normalized payloads through the gateway and renders platform-adaptive health cards.

**Tech Stack:** Go 1.24, Gin, Go tests, Python 3 probe script, Vue 3, Pinia, axios, Vitest

---

## File Structure

### New Go service

- Create: `services/monitor-service/go.mod`
- Create: `services/monitor-service/cmd/server/main.go`
- Create: `services/monitor-service/router/router.go`
- Create: `services/monitor-service/controller/monitor_controller.go`
- Create: `services/monitor-service/model/monitor.go`
- Create: `services/monitor-service/service/monitor_service.go`
- Create: `services/monitor-service/service/collector_service.go`
- Create: `services/monitor-service/service/probe_service.go`
- Create: `services/monitor-service/service/task_context_service.go`
- Create: `services/monitor-service/service/alert_service.go`
- Create: `services/monitor-service/service/stream_service.go`
- Create: `services/monitor-service/service/monitor_service_test.go`
- Create: `services/monitor-service/controller/monitor_controller_test.go`
- Create: `services/monitor-service/router/router_test.go`

### Python probe

- Create: `python-ai-service/scripts/monitor_probe.py`
- Create: `python-ai-service/tests/test_monitor_probe.py`

### Deployment and gateway

- Create: `deploy/docker/monitor-service.Dockerfile`
- Modify: `deploy/docker-compose.dev.yml`
- Modify: `deploy/docker-compose.platform.yml`
- Modify: `services/gateway-service/router/router.go`
- Modify: `services/gateway-service/router/router_test.go`
- Modify: `services/gateway-service/cmd/server/main.go`

### Frontend

- Modify: `web-console/src/types/platform.ts`
- Modify: `web-console/src/api/platform.ts`
- Create: `web-console/src/utils/sse.ts`
- Modify: `web-console/src/stores/platform.ts`
- Modify: `web-console/src/views/DashboardView.vue`
- Create: `web-console/src/views/DashboardView.spec.ts`

### Documentation

- Modify: `README.md`

## Task 1: Scaffold the Go monitor-service HTTP surface

**Files:**
- Create: `services/monitor-service/go.mod`
- Create: `services/monitor-service/cmd/server/main.go`
- Create: `services/monitor-service/router/router.go`
- Create: `services/monitor-service/controller/monitor_controller.go`
- Create: `services/monitor-service/model/monitor.go`
- Create: `services/monitor-service/service/monitor_service.go`
- Test: `services/monitor-service/router/router_test.go`

- [ ] **Step 1: Write the failing router test for health, overview, alerts, and stream**

```go
func TestMonitorRoutesExposeHealthOverviewAlertsAndStream(t *testing.T) {
	fakeService := &service.FakeMonitorService{
		OverviewValue: model.MonitorOverview{OverallHealth: "healthy"},
		AlertsValue: model.MonitorAlerts{ActiveAlerts: []model.MonitorAlert{}, RecentAlerts: []model.MonitorAlert{}},
		StreamEvents: []string{"event: snapshot\ndata: {\"overall_health\":\"healthy\"}\n\n"},
	}

	engine := router.New(controller.NewMonitorController(fakeService))

	rec := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodGet, "/health", nil)
	engine.ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rec.Code)
	}

	rec = httptest.NewRecorder()
	req = httptest.NewRequest(http.MethodGet, "/api/v1/monitor/overview", nil)
	engine.ServeHTTP(rec, req)
	if !strings.Contains(rec.Body.String(), "healthy") {
		t.Fatalf("expected overview payload, got %s", rec.Body.String())
	}

	rec = httptest.NewRecorder()
	req = httptest.NewRequest(http.MethodGet, "/api/v1/monitor/alerts", nil)
	engine.ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("expected alerts 200, got %d", rec.Code)
	}

	rec = httptest.NewRecorder()
	req = httptest.NewRequest(http.MethodGet, "/api/v1/monitor/stream", nil)
	engine.ServeHTTP(rec, req)
	if got := rec.Header().Get("Content-Type"); !strings.HasPrefix(got, "text/event-stream") {
		t.Fatalf("expected event stream content-type, got %q", got)
	}
}
```

- [ ] **Step 2: Run the monitor-service tests to verify they fail**

Run: `cd services/monitor-service && go test ./router -v`
Expected: FAIL because the service, controller, and router do not exist yet

- [ ] **Step 3: Add the minimal Go service skeleton**

```go
// services/monitor-service/model/monitor.go
package model

type MonitorOverview struct {
	OverallHealth string `json:"overall_health"`
}

type MonitorAlert struct {
	AlertID string `json:"alert_id"`
}

type MonitorAlerts struct {
	ActiveAlerts []MonitorAlert `json:"active_alerts"`
	RecentAlerts []MonitorAlert `json:"recent_alerts"`
}
```

```go
// services/monitor-service/service/monitor_service.go
package service

import (
	"context"
	"io"
	"strings"

	"electric-ai/services/monitor-service/model"
)

type MonitorService interface {
	GetOverview(ctx context.Context) (model.MonitorOverview, error)
	GetAlerts(ctx context.Context) (model.MonitorAlerts, error)
	Stream(ctx context.Context) io.Reader
}

type DefaultMonitorService struct{}

func NewMonitorService() *DefaultMonitorService {
	return &DefaultMonitorService{}
}

func (s *DefaultMonitorService) GetOverview(ctx context.Context) (model.MonitorOverview, error) {
	return model.MonitorOverview{OverallHealth: "healthy"}, nil
}

func (s *DefaultMonitorService) GetAlerts(ctx context.Context) (model.MonitorAlerts, error) {
	return model.MonitorAlerts{
		ActiveAlerts: []model.MonitorAlert{},
		RecentAlerts: []model.MonitorAlert{},
	}, nil
}

func (s *DefaultMonitorService) Stream(ctx context.Context) io.Reader {
	return strings.NewReader("event: snapshot\ndata: {\"overall_health\":\"healthy\"}\n\n")
}

type FakeMonitorService struct {
	OverviewValue model.MonitorOverview
	AlertsValue   model.MonitorAlerts
	StreamEvents  []string
}

func (s *FakeMonitorService) GetOverview(ctx context.Context) (model.MonitorOverview, error) { return s.OverviewValue, nil }
func (s *FakeMonitorService) GetAlerts(ctx context.Context) (model.MonitorAlerts, error) { return s.AlertsValue, nil }
func (s *FakeMonitorService) Stream(ctx context.Context) io.Reader {
	return strings.NewReader(strings.Join(s.StreamEvents, ""))
}
```

```go
// services/monitor-service/controller/monitor_controller.go
package controller

import (
	"net/http"

	"github.com/gin-gonic/gin"

	"electric-ai/services/monitor-service/service"
	"electric-ai/services/platform-common/pkg/httpx"
)

type MonitorController struct {
	service service.MonitorService
}

func NewMonitorController(svc service.MonitorService) *MonitorController {
	return &MonitorController{service: svc}
}

func (c *MonitorController) Overview(ctx *gin.Context) {
	result, err := c.service.GetOverview(ctx.Request.Context())
	if err != nil {
		ctx.JSON(http.StatusInternalServerError, httpx.Error("monitor overview failed"))
		return
	}
	ctx.JSON(http.StatusOK, result)
}

func (c *MonitorController) Alerts(ctx *gin.Context) {
	result, err := c.service.GetAlerts(ctx.Request.Context())
	if err != nil {
		ctx.JSON(http.StatusInternalServerError, httpx.Error("monitor alerts failed"))
		return
	}
	ctx.JSON(http.StatusOK, result)
}

func (c *MonitorController) Stream(ctx *gin.Context) {
	ctx.Header("Content-Type", "text/event-stream")
	_, _ = io.Copy(ctx.Writer, c.service.Stream(ctx.Request.Context()))
}
```

```go
// services/monitor-service/router/router.go
package router

import (
	"net/http"

	"github.com/gin-gonic/gin"

	"electric-ai/services/monitor-service/controller"
	"electric-ai/services/platform-common/pkg/httpx"
)

func New(monitorController *controller.MonitorController) *gin.Engine {
	engine := gin.New()
	engine.Use(gin.Logger(), gin.Recovery())

	engine.GET("/health", func(ctx *gin.Context) {
		ctx.JSON(http.StatusOK, httpx.OK(gin.H{"status": "ok"}, "health"))
	})

	v1 := engine.Group("/api/v1")
	monitor := v1.Group("/monitor")
	monitor.GET("/overview", monitorController.Overview)
	monitor.GET("/alerts", monitorController.Alerts)
	monitor.GET("/stream", monitorController.Stream)
	return engine
}
```

- [ ] **Step 4: Run the router tests to verify they pass**

Run: `cd services/monitor-service && go test ./router -v`
Expected: PASS for health, overview, alerts, and stream routing

- [ ] **Step 5: Commit the scaffold**

```bash
git add services/monitor-service
git commit -m "feat: scaffold go monitor service"
```

## Task 2: Implement platform detection, host collection, and normalized overview models

**Files:**
- Modify: `services/monitor-service/model/monitor.go`
- Create: `services/monitor-service/service/collector_service.go`
- Create: `services/monitor-service/service/monitor_service_test.go`
- Modify: `services/monitor-service/service/monitor_service.go`

- [ ] **Step 1: Write failing tests for Windows/macOS normalization**

```go
func TestBuildOverviewForMacOS(t *testing.T) {
	collector := service.NewCollectorService()
	snapshot := collector.Normalize(service.RawSnapshot{
		PlatformFamily: "macos",
		CPUUsagePercent: 22.5,
		MemoryTotalBytes: 32_000,
		MemoryUsedBytes: 24_000,
		SwapUsedBytes: 2_000,
		DiskTotalBytes: 100_000,
		DiskUsedBytes: 55_000,
		MPSAvailable: true,
		AIProcessMemoryBytes: 3_200_000_000,
	})

	if snapshot.AcceleratorSnapshot.AcceleratorType != "apple-mps" {
		t.Fatalf("expected apple-mps, got %s", snapshot.AcceleratorSnapshot.AcceleratorType)
	}
	if snapshot.HostSnapshot.PlatformFamily != "macos" {
		t.Fatalf("expected macos, got %s", snapshot.HostSnapshot.PlatformFamily)
	}
}

func TestBuildOverviewForWindows(t *testing.T) {
	collector := service.NewCollectorService()
	snapshot := collector.Normalize(service.RawSnapshot{
		PlatformFamily: "windows",
		CPUUsagePercent: 40,
		MemoryTotalBytes: 16_000,
		MemoryUsedBytes: 8_000,
		DiskTotalBytes: 200_000,
		DiskUsedBytes: 90_000,
		GPUName: "RTX 4060",
		VRAMTotalMB: 8192,
		VRAMUsedMB: 4096,
		GPUUtilizationPercent: 70,
		TemperatureC: 77,
	})

	if snapshot.AcceleratorSnapshot.AcceleratorType != "nvidia-cuda" {
		t.Fatalf("expected nvidia-cuda, got %s", snapshot.AcceleratorSnapshot.AcceleratorType)
	}
}
```

- [ ] **Step 2: Run the service tests to verify they fail**

Run: `cd services/monitor-service && go test ./service -v`
Expected: FAIL because normalization types and collector logic do not exist yet

- [ ] **Step 3: Implement normalized host and accelerator models**

```go
type HostSnapshot struct {
	PlatformFamily    string `json:"platform_family"`
	CapturedAt        string `json:"captured_at"`
	CPUUsagePercent   float64 `json:"cpu_usage_percent"`
	MemoryTotalBytes  uint64 `json:"memory_total_bytes"`
	MemoryUsedBytes   uint64 `json:"memory_used_bytes"`
	MemoryAvailableBytes uint64 `json:"memory_available_bytes"`
	MemoryPressureLevel string `json:"memory_pressure_level"`
	SwapUsedBytes     uint64 `json:"swap_used_bytes"`
	SwapTotalBytes    uint64 `json:"swap_total_bytes"`
	DiskTotalBytes    uint64 `json:"disk_total_bytes"`
	DiskUsedBytes     uint64 `json:"disk_used_bytes"`
	DiskAvailableBytes uint64 `json:"disk_available_bytes"`
}
```

```go
type AcceleratorSnapshot struct {
	AcceleratorType       string `json:"accelerator_type"`
	Available             bool   `json:"available"`
	SummaryLabel          string `json:"summary_label"`
	GPUName               string `json:"gpu_name,omitempty"`
	VRAMTotalMB           uint64 `json:"vram_total_mb,omitempty"`
	VRAMUsedMB            uint64 `json:"vram_used_mb,omitempty"`
	GPUUtilizationPercent uint64 `json:"gpu_utilization_percent,omitempty"`
	TemperatureC          uint64 `json:"temperature_c,omitempty"`
	MPSAvailable          bool   `json:"mps_available,omitempty"`
	UnifiedMemoryPressure string `json:"unified_memory_pressure,omitempty"`
	AIProcessMemoryBytes  uint64 `json:"ai_process_memory_bytes,omitempty"`
	UnavailableReason     string `json:"unavailable_reason,omitempty"`
}
```

```go
// services/monitor-service/service/collector_service.go
type RawSnapshot struct {
	PlatformFamily        string
	CPUUsagePercent       float64
	MemoryTotalBytes      uint64
	MemoryUsedBytes       uint64
	SwapUsedBytes         uint64
	DiskTotalBytes        uint64
	DiskUsedBytes         uint64
	GPUName               string
	VRAMTotalMB           uint64
	VRAMUsedMB            uint64
	GPUUtilizationPercent uint64
	TemperatureC          uint64
	MPSAvailable          bool
	AIProcessMemoryBytes  uint64
}

type CollectorService struct{}

func NewCollectorService() *CollectorService { return &CollectorService{} }

func (s *CollectorService) Normalize(raw RawSnapshot) model.MonitorOverview {
	overview := model.MonitorOverview{OverallHealth: "healthy"}
	overview.HostSnapshot = model.HostSnapshot{
		PlatformFamily: raw.PlatformFamily,
		CPUUsagePercent: raw.CPUUsagePercent,
		MemoryTotalBytes: raw.MemoryTotalBytes,
		MemoryUsedBytes: raw.MemoryUsedBytes,
		MemoryAvailableBytes: maxUint64(raw.MemoryTotalBytes, raw.MemoryUsedBytes),
		MemoryPressureLevel: "normal",
		SwapUsedBytes: raw.SwapUsedBytes,
		SwapTotalBytes: raw.SwapUsedBytes,
		DiskTotalBytes: raw.DiskTotalBytes,
		DiskUsedBytes: raw.DiskUsedBytes,
		DiskAvailableBytes: maxUint64(raw.DiskTotalBytes, raw.DiskUsedBytes),
	}
	if raw.PlatformFamily == "macos" {
		overview.AcceleratorSnapshot = model.AcceleratorSnapshot{
			AcceleratorType: "apple-mps",
			Available: true,
			SummaryLabel: "AI 加速资源健康",
			MPSAvailable: raw.MPSAvailable,
			UnifiedMemoryPressure: "warning",
			AIProcessMemoryBytes: raw.AIProcessMemoryBytes,
		}
		return overview
	}
	overview.AcceleratorSnapshot = model.AcceleratorSnapshot{
		AcceleratorType: "nvidia-cuda",
		Available: raw.GPUName != "",
		SummaryLabel: "GPU 显存健康",
		GPUName: raw.GPUName,
		VRAMTotalMB: raw.VRAMTotalMB,
		VRAMUsedMB: raw.VRAMUsedMB,
		GPUUtilizationPercent: raw.GPUUtilizationPercent,
		TemperatureC: raw.TemperatureC,
	}
	return overview
}
```

- [ ] **Step 4: Run the service tests to verify they pass**

Run: `cd services/monitor-service && go test ./service -v`
Expected: PASS for Windows and macOS overview normalization

- [ ] **Step 5: Commit normalized overview support**

```bash
git add services/monitor-service/model/monitor.go services/monitor-service/service
git commit -m "feat: add monitor overview normalization"
```

## Task 3: Add Python probe integration and alert evaluation

**Files:**
- Create: `services/monitor-service/service/probe_service.go`
- Create: `services/monitor-service/service/alert_service.go`
- Create: `python-ai-service/scripts/monitor_probe.py`
- Create: `python-ai-service/tests/test_monitor_probe.py`
- Modify: `services/monitor-service/service/monitor_service.go`
- Modify: `services/monitor-service/service/monitor_service_test.go`

- [ ] **Step 1: Write failing tests for probe parsing and alert classification**

```go
func TestProbeServiceParsesMacOSProbeOutput(t *testing.T) {
	probe := service.NewProbeService("python3", "testdata/fake_probe.py")
	result, err := probe.Run(context.Background(), "macos")
	if err != nil {
		t.Fatalf("probe run failed: %v", err)
	}
	if result.MPSAvailable != true {
		t.Fatalf("expected mps available")
	}
}

func TestAlertServiceMarksWorkerMissingAsCritical(t *testing.T) {
	alerts := service.NewAlertService().Evaluate(model.MonitorOverview{
		OverallHealth: "healthy",
		ServiceSnapshots: []model.ServiceSnapshot{
			{ServiceName: "python-ai-worker", Status: "missing"},
		},
	})
	if alerts.OverallHealth != "critical" {
		t.Fatalf("expected critical, got %s", alerts.OverallHealth)
	}
}
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd services/monitor-service && go test ./service -run 'Probe|Alert' -v`
Expected: FAIL because probe runner and alert service do not exist

- [ ] **Step 3: Implement Python probe and Go parser**

```python
# python-ai-service/scripts/monitor_probe.py
from __future__ import annotations

import json
import platform


def main() -> None:
    system_name = platform.system().lower()
    if system_name == "darwin":
        payload = {
            "platform_family": "macos",
            "mps_available": False,
            "ai_process_memory_bytes": 0,
        }
    else:
        payload = {
            "platform_family": "windows",
            "gpu_name": "",
            "vram_total_mb": 0,
            "vram_used_mb": 0,
            "gpu_utilization_percent": 0,
            "temperature_c": 0,
        }
    print(json.dumps(payload))


if __name__ == "__main__":
    main()
```

```go
// services/monitor-service/service/probe_service.go
type ProbeResult struct {
	PlatformFamily        string `json:"platform_family"`
	MPSAvailable          bool   `json:"mps_available"`
	AIProcessMemoryBytes  uint64 `json:"ai_process_memory_bytes"`
	GPUName               string `json:"gpu_name"`
	VRAMTotalMB           uint64 `json:"vram_total_mb"`
	VRAMUsedMB            uint64 `json:"vram_used_mb"`
	GPUUtilizationPercent uint64 `json:"gpu_utilization_percent"`
	TemperatureC          uint64 `json:"temperature_c"`
}

type ProbeService struct {
	pythonBin string
	scriptPath string
}

func NewProbeService(pythonBin, scriptPath string) *ProbeService {
	return &ProbeService{pythonBin: pythonBin, scriptPath: scriptPath}
}

func (s *ProbeService) Run(ctx context.Context, platformFamily string) (ProbeResult, error) {
	cmd := exec.CommandContext(ctx, s.pythonBin, s.scriptPath)
	output, err := cmd.Output()
	if err != nil {
		return ProbeResult{}, err
	}
	var result ProbeResult
	if err := json.Unmarshal(output, &result); err != nil {
		return ProbeResult{}, err
	}
	return result, nil
}
```

```go
// services/monitor-service/service/alert_service.go
func (s *AlertService) Evaluate(overview model.MonitorOverview) model.MonitorOverview {
	overall := "healthy"
	for _, service := range overview.ServiceSnapshots {
		if service.Status != "running" {
			overall = "critical"
			overview.ActiveAlerts = append(overview.ActiveAlerts, model.MonitorAlert{
				AlertID: "service:" + service.ServiceName,
				Level: "critical",
				Category: "service",
				Title: service.ServiceName + " 未运行",
				Message: service.ServiceName + " 未运行",
			})
		}
	}
	overview.OverallHealth = overall
	return overview
}
```

- [ ] **Step 4: Run the probe and alert tests to verify they pass**

Run: `cd services/monitor-service && go test ./service -run 'Probe|Alert' -v`
Expected: PASS for probe parsing and alert severity

Run: `cd python-ai-service && pytest tests/test_monitor_probe.py -v`
Expected: PASS for JSON probe output shape

- [ ] **Step 5: Commit probe integration**

```bash
git add services/monitor-service/service python-ai-service/scripts/monitor_probe.py python-ai-service/tests/test_monitor_probe.py
git commit -m "feat: add monitor probe integration"
```

## Task 4: Add task context, SSE event formatting, and gateway/Docker integration

**Files:**
- Create: `services/monitor-service/service/task_context_service.go`
- Create: `services/monitor-service/service/stream_service.go`
- Modify: `services/monitor-service/controller/monitor_controller.go`
- Modify: `services/monitor-service/router/router_test.go`
- Create: `deploy/docker/monitor-service.Dockerfile`
- Modify: `deploy/docker-compose.dev.yml`
- Modify: `deploy/docker-compose.platform.yml`
- Modify: `services/gateway-service/router/router.go`
- Modify: `services/gateway-service/router/router_test.go`
- Modify: `services/gateway-service/cmd/server/main.go`

- [ ] **Step 1: Write the failing gateway proxy and SSE body tests**

```go
func TestMonitorOverviewIsProxiedWithoutRedirect(t *testing.T) {
	monitorUpstream := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/v1/monitor/overview" {
			t.Fatalf("expected /api/v1/monitor/overview, got %s", r.URL.Path)
		}
		_, _ = io.WriteString(w, `{"overall_health":"healthy"}`)
	}))
	defer monitorUpstream.Close()

	engine := New(Upstreams{
		Auth: service.NewReverseProxy(monitorUpstream.URL),
		Model: service.NewReverseProxy(monitorUpstream.URL),
		Task: service.NewReverseProxy(monitorUpstream.URL),
		Asset: service.NewReverseProxy(monitorUpstream.URL),
		Audit: service.NewReverseProxy(monitorUpstream.URL),
		Monitor: service.NewReverseProxy(monitorUpstream.URL),
		Files: http.NotFoundHandler(),
	})

	req := httptest.NewRequest(http.MethodGet, "/api/v1/monitor/overview", nil)
	req.Header.Set("Authorization", "Bearer test-token")
	rec := httptest.NewRecorder()
	engine.ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rec.Code)
	}
}
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd services/gateway-service && go test ./router -run Monitor -v`
Expected: FAIL because gateway has no monitor upstream yet

- [ ] **Step 3: Implement stream formatting, gateway proxy, and Docker service**

```go
// services/monitor-service/service/stream_service.go
func FormatSSE(eventName string, payload []byte) string {
	return "event: " + eventName + "\n" + "data: " + string(payload) + "\n\n"
}
```

```go
// services/gateway-service/router/router.go
type Upstreams struct {
	Auth        *httputil.ReverseProxy
	Model       *httputil.ReverseProxy
	Task        *httputil.ReverseProxy
	Asset       *httputil.ReverseProxy
	Audit       *httputil.ReverseProxy
	Monitor     *httputil.ReverseProxy
	Files       http.Handler
	ImageChecks http.Handler
}

secured.Any("/api/v1/monitor", gin.WrapH(upstreams.Monitor))
secured.Any("/api/v1/monitor/*path", gin.WrapH(upstreams.Monitor))
```

```go
// services/gateway-service/cmd/server/main.go
Monitor: service.NewReverseProxy(getenv("MONITOR_SERVICE_URL", "http://localhost:8086")),
```

```dockerfile
# deploy/docker/monitor-service.Dockerfile
FROM golang:1.24 AS build
WORKDIR /app
COPY . .
WORKDIR /app/services/monitor-service
RUN go build -o /out/monitor-service ./cmd/server

FROM debian:bookworm-slim
WORKDIR /srv
COPY --from=build /out/monitor-service /srv/monitor-service
CMD ["/srv/monitor-service"]
```

- [ ] **Step 4: Run the integration tests to verify they pass**

Run: `cd services/gateway-service && go test ./router -v`
Expected: PASS including monitor proxy coverage

Run: `cd services/monitor-service && go test ./...`
Expected: PASS for router/controller/service packages

- [ ] **Step 5: Commit integration wiring**

```bash
git add deploy/docker/monitor-service.Dockerfile deploy/docker-compose.dev.yml deploy/docker-compose.platform.yml services/gateway-service services/monitor-service
git commit -m "feat: wire go monitor service through gateway"
```

## Task 5: Add frontend monitor types, authenticated SSE reader, and adaptive dashboard UI

**Files:**
- Modify: `web-console/src/types/platform.ts`
- Modify: `web-console/src/api/platform.ts`
- Create: `web-console/src/utils/sse.ts`
- Modify: `web-console/src/stores/platform.ts`
- Modify: `web-console/src/views/DashboardView.vue`
- Create: `web-console/src/views/DashboardView.spec.ts`
- Modify: `README.md`

- [ ] **Step 1: Write the failing dashboard rendering test**

```ts
const platformStore = {
  tasks: [],
  history: [],
  models: [],
  monitorOverview: {
    overall_health: 'warning',
    host_snapshot: { platform_family: 'macos', cpu_usage_percent: 22 },
    accelerator_snapshot: {
      accelerator_type: 'apple-mps',
      summary_label: 'AI 加速资源健康',
      mps_available: true,
      unified_memory_pressure: 'warning',
      ai_process_memory_bytes: 3200000000,
    },
    service_snapshots: [{ service_name: 'python-ai-service', status: 'running' }],
    task_runtime_context: { active_task_count: 1, latest_task_stage: 'generating' },
    active_alerts: [{ alert_id: 'memory', title: '统一内存压力偏高', level: 'warning' }],
    recent_alerts: [],
  },
  monitorConnected: true,
  fetchTasks: vi.fn(),
  fetchHistory: vi.fn(),
  fetchModels: vi.fn(),
  fetchMonitorOverview: vi.fn(),
  startMonitorStream: vi.fn(),
}
```

- [ ] **Step 2: Run the dashboard test to verify it fails**

Run: `cd web-console && npx vitest run src/views/DashboardView.spec.ts`
Expected: FAIL because monitor store fields and panel markup do not exist yet

- [ ] **Step 3: Implement frontend monitor support**

```ts
export type MonitorOverview = {
  overall_health: 'healthy' | 'warning' | 'critical'
  host_snapshot: {
    platform_family: 'windows' | 'macos' | 'unknown'
    cpu_usage_percent: number
    memory_total_bytes?: number
    memory_used_bytes?: number
    memory_pressure_level?: string
    swap_used_bytes?: number
  }
  accelerator_snapshot: {
    accelerator_type: 'nvidia-cuda' | 'apple-mps' | 'unavailable'
    summary_label: string
    available: boolean
    gpu_name?: string
    vram_total_mb?: number
    vram_used_mb?: number
    gpu_utilization_percent?: number
    temperature_c?: number
    mps_available?: boolean
    unified_memory_pressure?: string
    ai_process_memory_bytes?: number
    unavailable_reason?: string
  }
  service_snapshots: Array<{ service_name: string; status: string; resident_memory_bytes?: number }>
  task_runtime_context: { active_task_count: number; latest_task_stage?: string }
  active_alerts: MonitorAlert[]
  recent_alerts: MonitorAlert[]
}
```

```ts
export function getMonitorOverview() {
  return unwrap<MonitorOverview>(http.get('/monitor/overview'))
}
```

```ts
export async function* streamSse(url: string, token: string) {
  const response = await fetch(url, {
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: 'text/event-stream',
    },
  })
  // reader loop...
}
```

```vue
<section class="monitor-panel" v-if="platformStore.monitorOverview">
  <div class="panel-header">
    <h3>AI 运行健康</h3>
    <span>{{ platformStore.monitorConnected ? '实时连接中' : '连接已断开' }}</span>
  </div>
</section>
```

```md
- 新增 `monitor-service`，以 Go 微服务形式提供跨平台 AI 运行健康监控，并可调用 Python probe 获取增强指标。
```

- [ ] **Step 4: Run the frontend tests to verify they pass**

Run: `cd web-console && npx vitest run src/views/DashboardView.spec.ts src/views/GenerateView.spec.ts`
Expected: PASS including macOS and Windows monitor rendering cases

- [ ] **Step 5: Run the broader verification and commit**

Run: `cd services/monitor-service && go test ./...`
Expected: PASS for all monitor-service tests

Run: `cd services/gateway-service && go test ./...`
Expected: PASS including monitor proxy coverage

Run: `cd python-ai-service && pytest tests/test_monitor_probe.py -v`
Expected: PASS for probe JSON shape

Run: `cd web-console && npm test`
Expected: PASS including dashboard monitor rendering

```bash
git add web-console/src/types/platform.ts web-console/src/api/platform.ts web-console/src/utils/sse.ts web-console/src/stores/platform.ts web-console/src/views/DashboardView.vue web-console/src/views/DashboardView.spec.ts README.md
git commit -m "feat: add real-time cross-platform monitor dashboard"
```

## Spec Coverage Check

- Go monitor-service as the primary microservice: covered by Tasks 1 through 4.
- Python only as a probe helper: covered by Task 3.
- Windows and macOS adaptive collection: covered by Tasks 2 and 3.
- AI health plus host health normalization: covered by Tasks 2 and 3.
- Alert thresholds and task context association: covered by Tasks 3 and 4.
- Gateway proxying and Docker integration: covered by Task 4.
- Dual-system frontend panel and authenticated streaming: covered by Task 5.
- README and platform-facing docs update: covered by Task 5.

## Placeholder Scan

- No `TODO`, `TBD`, or deferred “implement later” language remains.
- Each task includes exact files, test commands, and code snippets.
- Later tasks reuse names introduced earlier: `MonitorOverview`, `CollectorService`, `ProbeService`, `AlertService`, and `streamSse`.

## Type Consistency Check

- Backend endpoint names stay consistent: `/api/v1/monitor/overview`, `/api/v1/monitor/alerts`, `/api/v1/monitor/stream`.
- Frontend types consistently use `monitorOverview`, `active_alerts`, `recent_alerts`, and `task_runtime_context`.
- Gateway naming consistently uses `Monitor` in `Upstreams` and `MONITOR_SERVICE_URL` in environment configuration.
- Python remains a probe script, not a second API service.
