# macOS 真实监控数据补齐 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the current macOS machine's monitor stack return real host, MPS, and key-process data instead of placeholder values, and surface that complete overview consistently to the monitor UI.

**Architecture:** Keep `Go monitor-service` as the primary API and collection layer, use `gopsutil` for real macOS host/process metrics, and call a rewritten Python probe only for MPS- and torch-runtime-specific data. Build one complete `MonitorOverview` per sample and reuse that same payload for both `/overview` and SSE so the frontend always sees the same shape.

**Tech Stack:** Go 1.24, `gin`, `gopsutil/v4`, Python 3, PyTorch MPS helpers, pytest, Vitest

---

## File Structure

- Modify: `services/monitor-service/go.mod`
- Modify: `services/monitor-service/model/monitor.go`
- Modify: `services/monitor-service/service/collector_service.go`
- Modify: `services/monitor-service/service/probe_service.go`
- Modify: `services/monitor-service/service/monitor_service.go`
- Modify: `services/monitor-service/service/alert_service.go`
- Modify: `services/monitor-service/service/monitor_service_test.go`
- Create: `services/monitor-service/service/collector_runtime_test.go`
- Modify: `python-ai-service/scripts/monitor_probe.py`
- Modify: `python-ai-service/tests/test_monitor_probe.py`
- Modify: `web-console/src/views/MonitorCockpitView.spec.ts`

### Task 1: Expand The Monitor Data Model For Real Process And Accelerator Fields

**Files:**
- Modify: `services/monitor-service/model/monitor.go`
- Modify: `services/monitor-service/service/monitor_service_test.go`
- Test: `services/monitor-service/service/monitor_service_test.go`

- [ ] **Step 1: Write the failing Go test for richer service and accelerator fields**

```go
func TestDefaultMonitorService_Stream_EmitsProcessAndAcceleratorDetails(t *testing.T) {
	overview := model.MonitorOverview{
		OverallHealth: "healthy",
		ServiceSnapshots: []model.ServiceSnapshot{
			{
				ServiceName:          "python-ai-service",
				DisplayName:          "Python AI Service",
				PID:                  123,
				Status:               "running",
				ResidentMemoryBytes:  512 * 1024 * 1024,
				CPUPercent:           14.5,
				SampleOK:             true,
			},
		},
		AcceleratorSnapshot: &model.AcceleratorSnapshot{
			AcceleratorType:       "apple-mps",
			SummaryLabel:          "MPS available",
			UnifiedMemoryPressure: "normal",
		},
		TaskRuntimeContext: model.TaskRuntimeContext{ActiveTaskCount: 0},
		ActiveAlerts:       []model.MonitorAlert{},
		RecentAlerts:       []model.MonitorAlert{},
	}

	fake := &fakeOverviewCollector{overview: overview}
	svc := NewDefaultMonitorServiceWithCollector(fake)

	reader, err := svc.Stream(context.Background())
	if err != nil {
		t.Fatalf("expected err=nil, got %v", err)
	}

	body, err := io.ReadAll(reader)
	if err != nil {
		t.Fatalf("expected SSE body, got err=%v", err)
	}

	if !strings.Contains(string(body), "\"display_name\":\"Python AI Service\"") {
		t.Fatalf("expected service display_name in SSE body, got %q", string(body))
	}
	if !strings.Contains(string(body), "\"pid\":123") {
		t.Fatalf("expected service pid in SSE body, got %q", string(body))
	}
	if !strings.Contains(string(body), "\"summary_label\":\"MPS available\"") {
		t.Fatalf("expected accelerator summary_label in SSE body, got %q", string(body))
	}
}
```

- [ ] **Step 2: Run the targeted Go test to verify RED**

Run: `go test ./service -run 'TestDefaultMonitorService_Stream_EmitsProcessAndAcceleratorDetails'`

Expected: FAIL because `ServiceSnapshot` does not yet include `display_name`, `pid`, `cpu_percent`, `sample_ok`, and the marshaled JSON cannot contain those fields.

- [ ] **Step 3: Add the new model fields with stable JSON names**

```go
type ServiceSnapshot struct {
	ServiceName         string  `json:"service_name"`
	DisplayName         string  `json:"display_name,omitempty"`
	PID                 int32   `json:"pid,omitempty"`
	Status              string  `json:"status"`
	UptimeSeconds       int64   `json:"uptime_seconds,omitempty"`
	CPUPercent          float64 `json:"cpu_percent,omitempty"`
	ResidentMemoryBytes uint64  `json:"resident_memory_bytes,omitempty"`
	SampleOK            bool    `json:"sample_ok"`
	SampleError         string  `json:"sample_error,omitempty"`
}
```

```go
type AcceleratorSnapshot struct {
	AcceleratorType       string  `json:"accelerator_type"`
	Available             *bool   `json:"available,omitempty"`
	SummaryLabel          string  `json:"summary_label,omitempty"`
	GPUName               string  `json:"gpu_name,omitempty"`
	VRAMTotalMB           int     `json:"vram_total_mb,omitempty"`
	VRAMUsedMB            int     `json:"vram_used_mb,omitempty"`
	GPUUtilizationPercent float64 `json:"gpu_utilization_percent,omitempty"`
	TemperatureC          float64 `json:"temperature_c,omitempty"`
	MPSAvailable          *bool   `json:"mps_available,omitempty"`
	UnifiedMemoryPressure string  `json:"unified_memory_pressure,omitempty"`
	AIProcessMemoryBytes  *uint64 `json:"ai_process_memory_bytes,omitempty"`
	UnavailableReason     string  `json:"unavailable_reason,omitempty"`
	PreferredDeviceType   string  `json:"preferred_device_type,omitempty"`
}
```

- [ ] **Step 4: Update the existing monitor service tests to populate the new required fields minimally**

```go
ServiceSnapshots: []model.ServiceSnapshot{
	{
		ServiceName:          "python-ai-service",
		Status:               "running",
		SampleOK:             true,
		ResidentMemoryBytes:  512 * 1024 * 1024,
	},
},
```

- [ ] **Step 5: Run the targeted Go tests to verify GREEN**

Run: `go test ./service -run 'TestDefaultMonitorService_Stream_EmitsProcessAndAcceleratorDetails|TestDefaultMonitorService_Stream_EmitsFullOverviewSnapshot'`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add services/monitor-service/model/monitor.go services/monitor-service/service/monitor_service_test.go
git commit -m "feat: expand monitor overview model"
```

### Task 2: Add Real macOS Host And Process Collection In Go

**Files:**
- Modify: `services/monitor-service/go.mod`
- Modify: `services/monitor-service/service/collector_service.go`
- Create: `services/monitor-service/service/collector_runtime_test.go`
- Test: `services/monitor-service/service/collector_runtime_test.go`

- [ ] **Step 1: Write the failing Go tests for real host snapshots and service snapshots**

```go
func TestCollectorService_CollectCurrentSnapshot_OnDarwinProducesRealHostValues(t *testing.T) {
	if runtime.GOOS != "darwin" {
		t.Skip("darwin-only runtime assertion")
	}

	cs := &CollectorService{}
	raw := cs.CollectCurrentSnapshot()

	if raw.Host.MemoryTotalBytes == 0 {
		t.Fatalf("expected non-zero memory_total_bytes on real macOS machine")
	}
	if raw.Host.DiskTotalBytes == 0 {
		t.Fatalf("expected non-zero disk_total_bytes on real macOS machine")
	}
	if raw.Host.CPUUsagePercent < 0 {
		t.Fatalf("expected cpu_usage_percent >= 0, got %v", raw.Host.CPUUsagePercent)
	}
}
```

```go
func TestCollectorService_NormalizeServiceSnapshots_ProducesKeyServiceRows(t *testing.T) {
	cs := &CollectorService{}

	snapshots := cs.normalizeServiceSnapshots([]rawServiceSample{
		{
			ServiceName:         "gateway-service",
			DisplayName:         "Gateway Service",
			PID:                 321,
			Status:              "running",
			ResidentMemoryBytes: 256,
			CPUPercent:          4.5,
			SampleOK:            true,
		},
	})

	if len(snapshots) != 3 {
		t.Fatalf("expected 3 key service rows, got %d", len(snapshots))
	}
	if snapshots[0].ServiceName == "" || snapshots[0].Status == "" {
		t.Fatalf("expected normalized service rows to be populated, got %+v", snapshots[0])
	}
}
```

- [ ] **Step 2: Run the targeted tests to verify RED**

Run: `go test ./service -run 'TestCollectorService_CollectCurrentSnapshot_OnDarwinProducesRealHostValues|TestCollectorService_NormalizeServiceSnapshots_ProducesKeyServiceRows'`

Expected: FAIL because `CollectCurrentSnapshot` still returns placeholder zero values and there is no real key-service normalization helper.

- [ ] **Step 3: Add `gopsutil` and wire real host collection**

```go
require (
	github.com/gin-gonic/gin v1.11.0
	github.com/shirou/gopsutil/v4 v4.25.4
)
```

```go
func (c *CollectorService) CollectCurrentSnapshot() RawSnapshot {
	now := time.Now().UTC()
	raw := RawSnapshot{
		Platform:   RawPlatform{OS: runtime.GOOS},
		CapturedAt: now,
	}

	raw.Host = c.collectHostSnapshot()
	raw.Services = c.collectServiceSamples()
	raw.Accelerator = c.collectPlatformAcceleratorPlaceholder(raw.Platform.OS)
	return raw
}
```

```go
func (c *CollectorService) collectHostSnapshot() RawHostSnapshot {
	result := RawHostSnapshot{}

	if cpuPercents, err := cpu.Percent(200*time.Millisecond, false); err == nil && len(cpuPercents) > 0 {
		result.CPUUsagePercent = cpuPercents[0]
	}

	if memInfo, err := mem.VirtualMemory(); err == nil {
		result.MemoryTotalBytes = memInfo.Total
		result.MemoryUsedBytes = memInfo.Used
		result.MemoryAvailBytes = memInfo.Available
	}

	if swapInfo, err := mem.SwapMemory(); err == nil {
		result.SwapTotalBytes = swapInfo.Total
		result.SwapUsedBytes = swapInfo.Used
	}

	if diskInfo, err := disk.Usage("/"); err == nil {
		result.DiskTotalBytes = diskInfo.Total
		result.DiskUsedBytes = diskInfo.Used
		result.DiskAvailBytes = diskInfo.Free
	}

	result.MemoryPressureRaw = deriveMemoryPressureLevel(result)
	return result
}
```

- [ ] **Step 4: Implement key-service process matching and normalized service rows**

```go
type rawServiceSample struct {
	ServiceName         string
	DisplayName         string
	PID                 int32
	Status              string
	UptimeSeconds       int64
	CPUPercent          float64
	ResidentMemoryBytes uint64
	SampleOK            bool
	SampleError         string
}
```

```go
func (c *CollectorService) normalizeServiceSnapshots(samples []rawServiceSample) []model.ServiceSnapshot {
	index := map[string]rawServiceSample{}
	for _, sample := range samples {
		if existing, ok := index[sample.ServiceName]; !ok || sample.ResidentMemoryBytes > existing.ResidentMemoryBytes {
			index[sample.ServiceName] = sample
		}
	}

	keys := []string{"gateway-service", "python-ai-service", "python-ai-worker"}
	rows := make([]model.ServiceSnapshot, 0, len(keys))
	for _, key := range keys {
		sample, ok := index[key]
		if !ok {
			rows = append(rows, model.ServiceSnapshot{
				ServiceName: key,
				Status:      "missing",
				SampleOK:    false,
				SampleError: "process not found",
			})
			continue
		}
		rows = append(rows, model.ServiceSnapshot{
			ServiceName:         sample.ServiceName,
			DisplayName:         sample.DisplayName,
			PID:                 sample.PID,
			Status:              sample.Status,
			UptimeSeconds:       sample.UptimeSeconds,
			CPUPercent:          sample.CPUPercent,
			ResidentMemoryBytes: sample.ResidentMemoryBytes,
			SampleOK:            sample.SampleOK,
			SampleError:         sample.SampleError,
		})
	}
	return rows
}
```

- [ ] **Step 5: Update normalization so `MonitorOverview.ServiceSnapshots` comes from the real process samples**

```go
func (c *CollectorService) Normalize(raw RawSnapshot) model.MonitorOverview {
	ov := model.MonitorOverview{
		OverallHealth:      "healthy",
		TaskRuntimeContext: model.TaskRuntimeContext{ActiveTaskCount: 0},
		ActiveAlerts:       []model.MonitorAlert{},
		RecentAlerts:       []model.MonitorAlert{},
	}

	ov.HostSnapshot = normalizeHost(raw)
	ov.AcceleratorSnapshot = normalizeAccelerator(raw)
	ov.ServiceSnapshots = c.normalizeServiceSnapshots(raw.Services)
	return ov
}
```

- [ ] **Step 6: Run the targeted Go tests to verify GREEN**

Run: `go test ./service -run 'TestCollectorService_CollectCurrentSnapshot_OnDarwinProducesRealHostValues|TestCollectorService_NormalizeServiceSnapshots_ProducesKeyServiceRows|TestCollectorService_CollectCurrentSnapshot_AcceleratorUnprobedSemantics'`

Expected: PASS on macOS

- [ ] **Step 7: Commit**

```bash
git add services/monitor-service/go.mod services/monitor-service/service/collector_service.go services/monitor-service/service/collector_runtime_test.go
git commit -m "feat: collect real macos host metrics"
```

### Task 3: Rewrite The Python Probe For Real MPS And Torch Device Data

**Files:**
- Modify: `python-ai-service/scripts/monitor_probe.py`
- Modify: `python-ai-service/tests/test_monitor_probe.py`
- Test: `python-ai-service/tests/test_monitor_probe.py`

- [ ] **Step 1: Write the failing Python tests for real macOS probe fields**

```python
from scripts import monitor_probe


def test_build_payload_for_macos_includes_preferred_device_and_reason(monkeypatch):
    monkeypatch.setattr(monitor_probe, "detect_mps_available", lambda: True)
    monkeypatch.setattr(monitor_probe, "detect_preferred_device_type", lambda: "mps")
    monkeypatch.setattr(monitor_probe, "measure_ai_process_memory_bytes", lambda: 987654321)

    payload = monitor_probe.build_payload("Darwin")

    assert payload["platform_family"] == "macos"
    assert payload["mps_available"] is True
    assert payload["preferred_device_type"] == "mps"
    assert payload["ai_process_memory_bytes"] == 987654321
    assert payload["unavailable_reason"] == ""
```

```python
def test_build_payload_for_macos_sets_reason_when_mps_is_unavailable(monkeypatch):
    monkeypatch.setattr(monitor_probe, "detect_mps_available", lambda: False)
    monkeypatch.setattr(monitor_probe, "detect_preferred_device_type", lambda: "cpu")
    monkeypatch.setattr(monitor_probe, "measure_ai_process_memory_bytes", lambda: 0)

    payload = monitor_probe.build_payload("Darwin")

    assert payload["mps_available"] is False
    assert payload["preferred_device_type"] == "cpu"
    assert payload["unavailable_reason"]
```

- [ ] **Step 2: Run the targeted pytest file to verify RED**

Run: `pytest tests/test_monitor_probe.py -v`

Expected: FAIL because `build_payload()` still returns only the placeholder keys.

- [ ] **Step 3: Rework `monitor_probe.py` around small, patchable helpers**

```python
from __future__ import annotations

import json
import platform
import subprocess

from app.core.torch_cuda import is_mps_available, preferred_torch_device_type
```

```python
def detect_mps_available() -> bool:
    return is_mps_available()


def detect_preferred_device_type() -> str:
    return preferred_torch_device_type()


def measure_ai_process_memory_bytes() -> int:
    try:
        output = subprocess.check_output(
            ["ps", "-axo", "rss=,command="],
            text=True,
        )
    except Exception:
        return 0

    total_kb = 0
    for line in output.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        parts = stripped.split(None, 1)
        if len(parts) != 2:
            continue
        rss_kb, command = parts
        if "python-ai-service" not in command and "worker.py" not in command:
            continue
        if not rss_kb.isdigit():
            continue
        total_kb += int(rss_kb)
    return total_kb * 1024
```

- [ ] **Step 4: Return a real macOS payload with explicit reason semantics**

```python
def build_payload(system_name: str | None = None) -> dict[str, object]:
    detected = (system_name or platform.system()).lower()
    if detected == "darwin":
        mps_available = detect_mps_available()
        preferred_device = detect_preferred_device_type()
        ai_process_memory_bytes = measure_ai_process_memory_bytes()
        return {
            "platform_family": "macos",
            "mps_available": mps_available,
            "preferred_device_type": preferred_device,
            "ai_process_memory_bytes": ai_process_memory_bytes,
            "unavailable_reason": "" if mps_available else "PyTorch MPS backend is not available on this machine",
        }

    return {
        "platform_family": "windows",
        "gpu_name": "",
        "vram_total_mb": 0,
        "vram_used_mb": 0,
        "gpu_utilization_percent": 0,
        "temperature_c": 0,
    }
```

- [ ] **Step 5: Run the targeted pytest file to verify GREEN**

Run: `pytest tests/test_monitor_probe.py -v`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add python-ai-service/scripts/monitor_probe.py python-ai-service/tests/test_monitor_probe.py
git commit -m "feat: add real macos monitor probe"
```

### Task 4: Bridge Probe Output Into Go Accelerator Snapshots

**Files:**
- Modify: `services/monitor-service/service/probe_service.go`
- Modify: `services/monitor-service/service/collector_service.go`
- Modify: `services/monitor-service/service/monitor_service_test.go`
- Test: `services/monitor-service/service/monitor_service_test.go`

- [ ] **Step 1: Write the failing Go test for preferred device and unavailable reason mapping**

```go
func TestCollectorService_Normalize_macOSProbeFieldsIntoAcceleratorSnapshot(t *testing.T) {
	cs := &CollectorService{}
	avail := false
	raw := RawSnapshot{
		Platform: RawPlatform{OS: "darwin"},
		Accelerator: RawAcceleratorSnapshot{
			AppleMPS: &RawAppleMPSSnapshot{
				MPSAvailable:          avail,
				UnifiedMemoryPressure: "warning",
				AIProcessMemoryBytes:  1024,
				PreferredDeviceType:   "cpu",
				UnavailableReason:     "PyTorch MPS backend is not available on this machine",
			},
		},
	}

	got := cs.Normalize(raw)

	if got.AcceleratorSnapshot == nil {
		t.Fatalf("expected accelerator snapshot")
	}
	if got.AcceleratorSnapshot.PreferredDeviceType != "cpu" {
		t.Fatalf("expected preferred_device_type=cpu, got %q", got.AcceleratorSnapshot.PreferredDeviceType)
	}
	if got.AcceleratorSnapshot.UnavailableReason == "" {
		t.Fatalf("expected unavailable_reason to be preserved")
	}
}
```

- [ ] **Step 2: Run the targeted Go test to verify RED**

Run: `go test ./service -run 'TestCollectorService_Normalize_macOSProbeFieldsIntoAcceleratorSnapshot|TestProbeServiceParsesMacOSProbeOutput'`

Expected: FAIL because `ProbeResult` and `RawAppleMPSSnapshot` do not yet carry `preferred_device_type` or explicit probe reason.

- [ ] **Step 3: Extend the probe result and raw accelerator structures**

```go
type ProbeResult struct {
	PlatformFamily       string `json:"platform_family"`
	MPSAvailable         bool   `json:"mps_available"`
	PreferredDeviceType  string `json:"preferred_device_type"`
	AIProcessMemoryBytes uint64 `json:"ai_process_memory_bytes"`
	UnavailableReason    string `json:"unavailable_reason"`
	GPUName              string `json:"gpu_name"`
	VRAMTotalMB          uint64 `json:"vram_total_mb"`
	VRAMUsedMB           uint64 `json:"vram_used_mb"`
	GPUUtilizationPercent float64 `json:"gpu_utilization_percent"`
	TemperatureC         float64 `json:"temperature_c"`
}
```

```go
type RawAppleMPSSnapshot struct {
	MPSAvailable          bool
	UnifiedMemoryPressure string
	AIProcessMemoryBytes  uint64
	PreferredDeviceType   string
	UnavailableReason     string
}
```

- [ ] **Step 4: Map probe output into the normalized accelerator snapshot**

```go
return &model.AcceleratorSnapshot{
	AcceleratorType:       "apple-mps",
	Available:             &avail,
	MPSAvailable:          &avail,
	UnifiedMemoryPressure: mps.UnifiedMemoryPressure,
	AIProcessMemoryBytes:  &mem,
	UnavailableReason:     reason,
	PreferredDeviceType:   mps.PreferredDeviceType,
	SummaryLabel:          buildMacAcceleratorSummary(avail, mps.PreferredDeviceType, mps.UnifiedMemoryPressure),
}
```

- [ ] **Step 5: Run the targeted Go tests to verify GREEN**

Run: `go test ./service -run 'TestCollectorService_Normalize_macOSProbeFieldsIntoAcceleratorSnapshot|TestProbeServiceParsesMacOSProbeOutput|TestCollectorService_Normalize_macOS_MPSNormalization'`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add services/monitor-service/service/probe_service.go services/monitor-service/service/collector_service.go services/monitor-service/service/monitor_service_test.go
git commit -m "feat: map macos probe data into accelerator snapshot"
```

### Task 5: Build The Real Overview Aggregation Path

**Files:**
- Modify: `services/monitor-service/service/monitor_service.go`
- Modify: `services/monitor-service/service/collector_service.go`
- Modify: `services/monitor-service/service/monitor_service_test.go`
- Test: `services/monitor-service/service/monitor_service_test.go`

- [ ] **Step 1: Write the failing Go test for overview reuse between HTTP and SSE**

```go
func TestDefaultMonitorService_Stream_ReusesRealOverviewPayload(t *testing.T) {
	fake := &fakeOverviewCollector{
		overview: model.MonitorOverview{
			OverallHealth: "healthy",
			HostSnapshot: &model.HostSnapshot{
				PlatformFamily:  "macos",
				CPUUsagePercent: 22,
			},
			ServiceSnapshots: []model.ServiceSnapshot{
				{ServiceName: "gateway-service", Status: "running", SampleOK: true},
			},
			TaskRuntimeContext: model.TaskRuntimeContext{ActiveTaskCount: 0},
			ActiveAlerts:       []model.MonitorAlert{},
			RecentAlerts:       []model.MonitorAlert{},
		},
	}
	svc := NewDefaultMonitorServiceWithCollector(fake)

	overview, err := svc.GetOverview(context.Background())
	if err != nil {
		t.Fatalf("expected GetOverview err=nil, got %v", err)
	}
	reader, err := svc.Stream(context.Background())
	if err != nil {
		t.Fatalf("expected Stream err=nil, got %v", err)
	}
	body, _ := io.ReadAll(reader)

	if !strings.Contains(string(body), "\"cpu_usage_percent\":22") {
		t.Fatalf("expected SSE payload to contain the same overview body, got %q", string(body))
	}
	if overview.HostSnapshot == nil || overview.HostSnapshot.CPUUsagePercent != 22 {
		t.Fatalf("expected overview CPU value to remain 22, got %+v", overview.HostSnapshot)
	}
}
```

- [ ] **Step 2: Run the targeted Go tests to verify RED**

Run: `go test ./service -run 'TestDefaultMonitorService_Stream_ReusesRealOverviewPayload|TestDefaultMonitorService_GetOverview_UsesCollectorAndEvaluatesAlerts'`

Expected: FAIL once probe-aware aggregation is introduced but not yet wired consistently.

- [ ] **Step 3: Make `DefaultMonitorService` assemble one real overview per request**

```go
func (s *DefaultMonitorService) buildOverview(ctx context.Context) (model.MonitorOverview, error) {
	raw := s.collector.CollectCurrentSnapshot()
	overview := s.collector.Normalize(raw)
	overview = NewAlertService().Evaluate(overview)
	overview.ActiveAlerts = ensureAlerts(overview.ActiveAlerts)
	overview.RecentAlerts = ensureRecentAlerts(overview.RecentAlerts)
	return overview, nil
}

func (s *DefaultMonitorService) GetOverview(ctx context.Context) (model.MonitorOverview, error) {
	return s.buildOverview(ctx)
}
```

```go
func (s *DefaultMonitorService) Stream(ctx context.Context) (io.Reader, error) {
	overview, err := s.buildOverview(ctx)
	if err != nil {
		return nil, err
	}
	payload, err := json.Marshal(overview)
	if err != nil {
		return nil, fmt.Errorf("marshal monitor overview for sse: %w", err)
	}
	return strings.NewReader(FormatSSE("snapshot", payload)), nil
}
```

- [ ] **Step 4: Run the targeted Go tests to verify GREEN**

Run: `go test ./service -run 'TestDefaultMonitorService_Stream_ReusesRealOverviewPayload|TestDefaultMonitorService_Stream_EmitsFullOverviewSnapshot|TestDefaultMonitorService_GetOverview_UsesCollectorAndEvaluatesAlerts'`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add services/monitor-service/service/monitor_service.go services/monitor-service/service/collector_service.go services/monitor-service/service/monitor_service_test.go
git commit -m "feat: unify real monitor overview output"
```

### Task 6: Upgrade Alert Rules For Real macOS Host And MPS Conditions

**Files:**
- Modify: `services/monitor-service/service/alert_service.go`
- Modify: `services/monitor-service/service/monitor_service_test.go`
- Test: `services/monitor-service/service/monitor_service_test.go`

- [ ] **Step 1: Write the failing Go tests for MPS and memory pressure alerts**

```go
func TestAlertServiceAddsMPSUnavailableAlertWhenPythonRuntimeIsRunning(t *testing.T) {
	avail := false
	ov := model.MonitorOverview{
		OverallHealth: "healthy",
		AcceleratorSnapshot: &model.AcceleratorSnapshot{
			AcceleratorType:   "apple-mps",
			Available:         &avail,
			UnavailableReason: "PyTorch MPS backend is not available on this machine",
		},
		ServiceSnapshots: []model.ServiceSnapshot{
			{ServiceName: "python-ai-service", Status: "running", SampleOK: true},
			{ServiceName: "python-ai-worker", Status: "running", SampleOK: true},
			{ServiceName: "gateway-service", Status: "running", SampleOK: true},
		},
	}

	got := NewAlertService().Evaluate(ov)

	if !strings.Contains(formatAlertIDs(got.ActiveAlerts), "accelerator:mps-unavailable") {
		t.Fatalf("expected accelerator:mps-unavailable alert, got %+v", got.ActiveAlerts)
	}
}
```

```go
func TestAlertServiceAddsMemoryPressureAlert(t *testing.T) {
	ov := model.MonitorOverview{
		OverallHealth: "healthy",
		HostSnapshot: &model.HostSnapshot{
			MemoryPressureLevel: "critical",
		},
		ServiceSnapshots: []model.ServiceSnapshot{
			{ServiceName: "python-ai-service", Status: "running", SampleOK: true},
			{ServiceName: "python-ai-worker", Status: "running", SampleOK: true},
			{ServiceName: "gateway-service", Status: "running", SampleOK: true},
		},
	}

	got := NewAlertService().Evaluate(ov)

	if !strings.Contains(formatAlertIDs(got.ActiveAlerts), "host:memory-pressure") {
		t.Fatalf("expected host:memory-pressure alert, got %+v", got.ActiveAlerts)
	}
}
```

- [ ] **Step 2: Run the targeted Go tests to verify RED**

Run: `go test ./service -run 'TestAlertServiceAddsMPSUnavailableAlertWhenPythonRuntimeIsRunning|TestAlertServiceAddsMemoryPressureAlert'`

Expected: FAIL because `AlertService` still only builds `service:*` alerts.

- [ ] **Step 3: Extend `AlertService.Evaluate()` with accelerator and host alert builders**

```go
func (s *AlertService) Evaluate(overview model.MonitorOverview) model.MonitorOverview {
	kept := keepNonServiceAlerts(overview.ActiveAlerts)
	serviceAlerts, critical := buildServiceAlerts(overview.ServiceSnapshots, overview.OverallHealth)
	extraAlerts, extraCritical := buildMacHealthAlerts(overview)

	if critical || extraCritical {
		overview.OverallHealth = "critical"
	}
	if !critical && !extraCritical && len(serviceAlerts) == 0 && len(extraAlerts) > 0 {
		overview.OverallHealth = "warning"
	}

	overview.ActiveAlerts = append(kept, serviceAlerts...)
	overview.ActiveAlerts = append(overview.ActiveAlerts, extraAlerts...)
	return overview
}
```

- [ ] **Step 4: Run the targeted Go tests to verify GREEN**

Run: `go test ./service -run 'TestAlertServiceAddsMPSUnavailableAlertWhenPythonRuntimeIsRunning|TestAlertServiceAddsMemoryPressureAlert|TestAlertServiceEvaluateDoesNotDuplicateServiceAlerts'`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add services/monitor-service/service/alert_service.go services/monitor-service/service/monitor_service_test.go
git commit -m "feat: add macos monitor health alerts"
```

### Task 7: Verify The Frontend Can Explain Real macOS Accelerator Data

**Files:**
- Modify: `web-console/src/views/MonitorCockpitView.spec.ts`
- Test: `web-console/src/views/MonitorCockpitView.spec.ts`

- [ ] **Step 1: Write the failing frontend view test for real macOS accelerator copy**

```ts
it('renders real MPS detail copy when macOS accelerator data is present without fake GPU percentages', async () => {
  platformStore.monitorConnected = true
  platformStore.monitorOverview = {
    overall_health: 'warning',
    host_snapshot: {
      platform_family: 'macos',
      cpu_usage_percent: 31,
      memory_total_bytes: 1600,
      memory_used_bytes: 800,
      memory_pressure_level: 'warning',
    },
    accelerator_snapshot: {
      accelerator_type: 'apple-mps',
      available: true,
      mps_available: true,
      preferred_device_type: 'mps',
      unified_memory_pressure: 'warning',
      ai_process_memory_bytes: 1073741824,
      summary_label: 'MPS available',
    },
    service_snapshots: [{ service_name: 'gateway-service', status: 'running' }],
    task_runtime_context: { active_task_count: 0 },
    active_alerts: [],
    recent_alerts: [],
  }

  const html = await renderView()

  expect(html).toContain('apple-mps')
  expect(html).toContain('unified pressure: warning')
  expect(html).toContain('N/A')
})
```

- [ ] **Step 2: Run the targeted frontend test to verify RED**

Run: `npm test -- src/views/MonitorCockpitView.spec.ts`

Expected: FAIL if the view assumptions still treat missing GPU utilization as generic missing data rather than valid macOS accelerator detail.

- [ ] **Step 3: Adjust only the view-level expectations or copy needed for real macOS MPS semantics**

```ts
const acceleratorMissingReason = computed(() => {
  const accelerator = overview.value?.accelerator_snapshot
  if (!accelerator) {
    return '缺少 accelerator_snapshot'
  }
  if (accelerator.accelerator_type === 'apple-mps' && accelerator.available) {
    return ''
  }
  if (acceleratorPercent.value != null) {
    return ''
  }
  return accelerator.unavailable_reason || '缺少 gpu_utilization_percent 或 VRAM 指标'
})
```

- [ ] **Step 4: Run the targeted frontend test to verify GREEN**

Run: `npm test -- src/views/MonitorCockpitView.spec.ts`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web-console/src/views/MonitorCockpitView.spec.ts web-console/src/views/MonitorCockpitView.vue
git commit -m "test: cover macos real monitor accelerator copy"
```

### Task 8: End-To-End Local Verification On This macOS Machine

**Files:**
- Modify: `services/monitor-service/service/collector_runtime_test.go`
- Test: `services/monitor-service/service/collector_runtime_test.go`

- [ ] **Step 1: Add a darwin-only smoke-style runtime assertion for non-placeholder values**

```go
func TestCollectorService_CollectCurrentSnapshot_DarwinSmoke(t *testing.T) {
	if runtime.GOOS != "darwin" {
		t.Skip("darwin-only smoke assertion")
	}

	cs := &CollectorService{}
	raw := cs.CollectCurrentSnapshot()
	got := cs.Normalize(raw)

	if got.HostSnapshot == nil {
		t.Fatalf("expected host snapshot")
	}
	if got.HostSnapshot.MemoryTotalBytes == 0 {
		t.Fatalf("expected real memory_total_bytes, got 0")
	}
	if got.HostSnapshot.DiskTotalBytes == 0 {
		t.Fatalf("expected real disk_total_bytes, got 0")
	}
	if got.ServiceSnapshots == nil {
		t.Fatalf("expected service snapshots slice")
	}
}
```

- [ ] **Step 2: Run all monitor-service Go tests**

Run: `go test ./...`

Expected: PASS

- [ ] **Step 3: Run the Python probe tests**

Run: `pytest tests/test_monitor_probe.py -v`

Expected: PASS

- [ ] **Step 4: Boot or restart the monitor service locally and inspect the real overview payload**

Run: `go run ./cmd/server`

Expected: service starts on configured port without panic

- [ ] **Step 5: Query the monitor overview endpoint from another shell**

Run: `curl -s http://127.0.0.1:8086/api/v1/monitor/overview`

Expected: JSON contains non-zero `memory_total_bytes`, non-zero `disk_total_bytes`, a populated `accelerator_snapshot.accelerator_type`, and stable `service_snapshots`

- [ ] **Step 6: Query the monitor SSE endpoint once**

Run: `curl -N http://127.0.0.1:8086/api/v1/monitor/stream`

Expected: one `event: snapshot` message whose JSON body includes the same `host_snapshot`, `accelerator_snapshot`, and `service_snapshots` structure as `/overview`

- [ ] **Step 7: Run the targeted frontend monitor tests**

Run: `npm test -- src/stores/platform.spec.ts src/views/MonitorCockpitView.spec.ts`

Expected: PASS

- [ ] **Step 8: Commit any final verification-only test updates**

```bash
git add services/monitor-service/service/collector_runtime_test.go
git commit -m "test: verify real macos monitor collection"
```
