package service

import (
	"bufio"
	"context"
	"electric-ai/services/monitor-service/model"
	"encoding/json"
	"errors"
	"io"
	"os"
	"path/filepath"
	"reflect"
	"runtime"
	"strings"
	"testing"
	"time"
)

func TestCollectorService_Normalize_macOS_MPSNormalization(t *testing.T) {
	cs := &CollectorService{}

	capturedAt := time.Date(2026, 5, 2, 12, 0, 0, 0, time.UTC)
	raw := RawSnapshot{
		Platform:   RawPlatform{OS: "darwin"},
		CapturedAt: capturedAt,
		Host: RawHostSnapshot{
			CPUUsagePercent:  17.5,
			MemoryTotalBytes: 16 * 1024 * 1024 * 1024,
			MemoryUsedBytes:  6 * 1024 * 1024 * 1024,
		},
		Accelerator: RawAcceleratorSnapshot{
			AppleMPS: &RawAppleMPSSnapshot{
				MPSAvailable:          true,
				AIProcessMemoryBytes:  512 * 1024 * 1024,
				UnifiedMemoryPressure: "normal",
			},
		},
	}

	got := cs.Normalize(raw)

	if got.HostSnapshot == nil {
		t.Fatalf("expected overview.host_snapshot to be set")
	}
	if got.HostSnapshot.PlatformFamily != "macos" {
		t.Fatalf("expected platform_family=macos, got %q", got.HostSnapshot.PlatformFamily)
	}
	if got.HostSnapshot.CapturedAt == nil || !got.HostSnapshot.CapturedAt.Equal(capturedAt) {
		t.Fatalf("expected captured_at=%s, got %v", capturedAt.Format(time.RFC3339Nano), got.HostSnapshot.CapturedAt)
	}
	if got.HostSnapshot.MemoryAvailableBytes != got.HostSnapshot.MemoryTotalBytes-got.HostSnapshot.MemoryUsedBytes {
		t.Fatalf("expected memory_available_bytes to be derived as total-used, got %d", got.HostSnapshot.MemoryAvailableBytes)
	}

	if got.AcceleratorSnapshot == nil {
		t.Fatalf("expected overview.accelerator_snapshot to be set")
	}
	if got.AcceleratorSnapshot.AcceleratorType != "apple-mps" {
		t.Fatalf("expected accelerator_type=apple-mps, got %q", got.AcceleratorSnapshot.AcceleratorType)
	}
	if got.AcceleratorSnapshot.MPSAvailable == nil || *got.AcceleratorSnapshot.MPSAvailable != true {
		t.Fatalf("expected mps_available=true, got %v", got.AcceleratorSnapshot.MPSAvailable)
	}
	if got.AcceleratorSnapshot.AIProcessMemoryBytes == nil || *got.AcceleratorSnapshot.AIProcessMemoryBytes != 512*1024*1024 {
		t.Fatalf("expected ai_process_memory_bytes preserved, got %v", got.AcceleratorSnapshot.AIProcessMemoryBytes)
	}
}

func TestCollectorService_Normalize_Windows_NvidiaCudaNormalization(t *testing.T) {
	cs := &CollectorService{}

	raw := RawSnapshot{
		Platform: RawPlatform{OS: "windows"},
		Accelerator: RawAcceleratorSnapshot{
			NvidiaCUDA: &RawNvidiaCUDASnapshot{
				GPUName:               "NVIDIA GeForce RTX 4060",
				VRAMTotalMB:           8192,
				VRAMUsedMB:            2048,
				GPUUtilizationPercent: 33.0,
				TemperatureC:          61.5,
				Available:             true,
				SummaryLabel:          "CUDA OK",
			},
		},
	}

	got := cs.Normalize(raw)

	if got.AcceleratorSnapshot == nil {
		t.Fatalf("expected overview.accelerator_snapshot to be set")
	}
	if got.AcceleratorSnapshot.AcceleratorType != "nvidia-cuda" {
		t.Fatalf("expected accelerator_type=nvidia-cuda, got %q", got.AcceleratorSnapshot.AcceleratorType)
	}
	if got.AcceleratorSnapshot.GPUName != "NVIDIA GeForce RTX 4060" {
		t.Fatalf("expected gpu_name preserved, got %q", got.AcceleratorSnapshot.GPUName)
	}
	if got.AcceleratorSnapshot.VRAMTotalMB != 8192 || got.AcceleratorSnapshot.VRAMUsedMB != 2048 {
		t.Fatalf("expected vram fields preserved, got total=%d used=%d", got.AcceleratorSnapshot.VRAMTotalMB, got.AcceleratorSnapshot.VRAMUsedMB)
	}
	if got.AcceleratorSnapshot.GPUUtilizationPercent != 33.0 {
		t.Fatalf("expected gpu_utilization_percent preserved, got %v", got.AcceleratorSnapshot.GPUUtilizationPercent)
	}
	if got.AcceleratorSnapshot.TemperatureC != 61.5 {
		t.Fatalf("expected temperature_c preserved, got %v", got.AcceleratorSnapshot.TemperatureC)
	}
}

func TestDefaultMonitorService_GetOverview_UsesCollectorAndEvaluatesAlerts(t *testing.T) {
	raw := RawSnapshot{
		Platform:   RawPlatform{OS: "darwin"},
		CapturedAt: time.Date(2026, 5, 2, 0, 0, 0, 0, time.UTC),
		Accelerator: RawAcceleratorSnapshot{
			AppleMPS: &RawAppleMPSSnapshot{MPSAvailable: false},
		},
	}
	want := (&CollectorService{}).Normalize(raw)

	fake := &fakeOverviewCollector{
		raw:      raw,
		overview: want,
	}
	svc := NewDefaultMonitorServiceWithCollector(fake)

	got, err := svc.GetOverview(context.Background())
	if err != nil {
		t.Fatalf("expected err=nil, got %v", err)
	}
	wantEvaluated := NewAlertService().Evaluate(want)
	wantEvaluated.RecentAlerts = []model.MonitorAlert{}
	if !reflect.DeepEqual(got, wantEvaluated) {
		t.Fatalf("expected GetOverview to return evaluated overview")
	}
	if fake.collectCalls != 1 || fake.normalizeCalls != 1 {
		t.Fatalf("expected 1 collect + 1 normalize call, got collect=%d normalize=%d", fake.collectCalls, fake.normalizeCalls)
	}
}

func TestDefaultMonitorService_Stream_EmitsFullOverviewSnapshot(t *testing.T) {
	raw := RawSnapshot{
		Platform: RawPlatform{OS: "darwin"},
		Host: RawHostSnapshot{
			CPUUsagePercent: 42,
		},
	}
	overview := model.MonitorOverview{
		OverallHealth: "warning",
		HostSnapshot: &model.HostSnapshot{
			PlatformFamily:  "macos",
			CPUUsagePercent: 42,
		},
		ServiceSnapshots: []model.ServiceSnapshot{
			{
				ServiceName:         "python-ai-service",
				Status:              "running",
				SampleOK:            true,
				ResidentMemoryBytes: 512 * 1024 * 1024,
			},
		},
		TaskRuntimeContext: model.TaskRuntimeContext{
			ActiveTaskCount: 1,
			LatestTaskStage: "generating",
		},
		ActiveAlerts: []model.MonitorAlert{
			{AlertID: "latency", Level: "warning", Title: "推理延迟偏高", Message: "latency high"},
		},
		RecentAlerts: []model.MonitorAlert{},
	}

	fake := &fakeOverviewCollector{
		raw:      raw,
		overview: overview,
	}
	svc := NewDefaultMonitorServiceWithCollector(fake)

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	reader, err := svc.Stream(ctx)
	if err != nil {
		t.Fatalf("expected err=nil, got %v", err)
	}

	frame, err := readNextSSEFrame(bufio.NewReader(reader))
	if err != nil {
		t.Fatalf("expected first SSE frame, got err=%v", err)
	}
	got := frame
	if !strings.Contains(got, "event: snapshot") {
		t.Fatalf("expected snapshot event, got %q", got)
	}
	if !strings.Contains(got, "\"host_snapshot\"") {
		t.Fatalf("expected full overview payload to include host_snapshot, got %q", got)
	}
	if !strings.Contains(got, "\"task_runtime_context\"") {
		t.Fatalf("expected full overview payload to include task_runtime_context, got %q", got)
	}
	if !strings.Contains(got, "\"recent_alerts\":[]") {
		t.Fatalf("expected full overview payload to include recent_alerts, got %q", got)
	}
	if !strings.Contains(got, "\"sample_ok\":true") {
		t.Fatalf("expected full overview payload to include sample_ok=true for service snapshot, got %q", got)
	}

	encoded := strings.TrimPrefix(frame, "event: snapshot\n")
	lines := strings.Split(strings.TrimSpace(encoded), "\n")
	dataLines := make([]string, 0, len(lines))
	for _, line := range lines {
		if strings.HasPrefix(line, "data: ") {
			dataLines = append(dataLines, strings.TrimPrefix(line, "data: "))
		}
	}

	var payload model.MonitorOverview
	if err := json.Unmarshal([]byte(strings.Join(dataLines, "\n")), &payload); err != nil {
		t.Fatalf("expected valid json payload, got err=%v body=%q", err, got)
	}
	if payload.HostSnapshot == nil || payload.HostSnapshot.PlatformFamily != "macos" {
		t.Fatalf("expected host_snapshot.platform_family=macos, got %+v", payload.HostSnapshot)
	}
	if payload.TaskRuntimeContext.LatestTaskStage != "generating" {
		t.Fatalf("expected latest_task_stage=generating, got %+v", payload.TaskRuntimeContext)
	}
}

func TestDefaultMonitorService_Stream_EmitsProcessAndAcceleratorDetails(t *testing.T) {
	overview := model.MonitorOverview{
		OverallHealth: "healthy",
		ServiceSnapshots: []model.ServiceSnapshot{
			{
				ServiceName:         "python-ai-service",
				DisplayName:         "Python AI Service",
				PID:                 123,
				Status:              "running",
				ResidentMemoryBytes: 512 * 1024 * 1024,
				CPUPercent:          14.5,
				SampleOK:            true,
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

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	reader, err := svc.Stream(ctx)
	if err != nil {
		t.Fatalf("expected err=nil, got %v", err)
	}

	body, err := readNextSSEFrame(bufio.NewReader(reader))
	if err != nil {
		t.Fatalf("expected first SSE frame, got err=%v", err)
	}

	if !strings.Contains(body, "\"display_name\":\"Python AI Service\"") {
		t.Fatalf("expected service display_name in SSE body, got %q", body)
	}
	if !strings.Contains(body, "\"pid\":123") {
		t.Fatalf("expected service pid in SSE body, got %q", body)
	}
	if !strings.Contains(body, "\"summary_label\":\"MPS available\"") {
		t.Fatalf("expected accelerator summary_label in SSE body, got %q", body)
	}
}

func TestDefaultMonitorService_Stream_EmitsContinuousSnapshotsUntilContextCancel(t *testing.T) {
	overview := model.MonitorOverview{
		OverallHealth: "healthy",
		ServiceSnapshots: []model.ServiceSnapshot{
			{ServiceName: "python-ai-service", Status: "running", SampleOK: true},
		},
		TaskRuntimeContext: model.TaskRuntimeContext{ActiveTaskCount: 0},
		ActiveAlerts:       []model.MonitorAlert{},
		RecentAlerts:       []model.MonitorAlert{},
	}

	fake := &fakeOverviewCollector{overview: overview}
	svc := NewDefaultMonitorServiceWithCollector(fake)

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	reader, err := svc.Stream(ctx)
	if err != nil {
		t.Fatalf("expected err=nil, got %v", err)
	}

	br := bufio.NewReader(reader)
	start := time.Now()

	firstFrame, err := readNextSSEFrame(br)
	if err != nil {
		t.Fatalf("expected first SSE frame, got err=%v", err)
	}
	if !strings.Contains(firstFrame, "event: snapshot") {
		t.Fatalf("expected first frame to be snapshot event, got %q", firstFrame)
	}

	secondFrame, err := readNextSSEFrame(br)
	if err != nil {
		t.Fatalf("expected second SSE frame, got err=%v", err)
	}
	if !strings.Contains(secondFrame, "event: snapshot") {
		t.Fatalf("expected second frame to be snapshot event, got %q", secondFrame)
	}

	if elapsed := time.Since(start); elapsed < 900*time.Millisecond {
		t.Fatalf("expected at least ~1s between frame 1 and frame 2, got %v", elapsed)
	}
	if fake.collectCalls < 2 || fake.normalizeCalls < 2 {
		t.Fatalf("expected collector invoked for each frame, got collect=%d normalize=%d", fake.collectCalls, fake.normalizeCalls)
	}

	cancel()

	_, err = readNextSSEFrame(br)
	if err == nil {
		t.Fatalf("expected stream read to stop after context cancellation")
	}
	if !errors.Is(err, context.Canceled) && !errors.Is(err, io.EOF) {
		t.Fatalf("expected context cancellation or EOF, got err=%v", err)
	}
}

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

func TestCollectorService_CollectCurrentSnapshot_AcceleratorUnprobedSemantics(t *testing.T) {
	cs := &CollectorService{}
	raw := cs.CollectCurrentSnapshot()
	got := cs.Normalize(raw)

	switch runtime.GOOS {
	case "darwin":
		if got.AcceleratorSnapshot == nil {
			t.Fatalf("expected accelerator_snapshot non-nil on darwin")
		}
		if got.AcceleratorSnapshot.AcceleratorType != "apple-mps" {
			t.Fatalf("expected accelerator_type=apple-mps, got %q", got.AcceleratorSnapshot.AcceleratorType)
		}
		if got.AcceleratorSnapshot.Available == nil || *got.AcceleratorSnapshot.Available != false {
			t.Fatalf("expected available=false on darwin, got %v", got.AcceleratorSnapshot.Available)
		}
		if got.AcceleratorSnapshot.UnavailableReason == "" {
			t.Fatalf("expected unavailable_reason to be set on darwin")
		}
	case "windows":
		if got.AcceleratorSnapshot == nil {
			t.Fatalf("expected accelerator_snapshot non-nil on windows")
		}
		if got.AcceleratorSnapshot.AcceleratorType != "nvidia-cuda" {
			t.Fatalf("expected accelerator_type=nvidia-cuda, got %q", got.AcceleratorSnapshot.AcceleratorType)
		}
		if got.AcceleratorSnapshot.Available == nil || *got.AcceleratorSnapshot.Available != false {
			t.Fatalf("expected available=false on windows, got %v", got.AcceleratorSnapshot.Available)
		}
		if got.AcceleratorSnapshot.UnavailableReason == "" {
			t.Fatalf("expected unavailable_reason to be set on windows")
		}
	default:
		if got.AcceleratorSnapshot != nil {
			t.Fatalf("expected accelerator_snapshot=nil on %s", runtime.GOOS)
		}
	}
}

func TestProbeServiceParsesMacOSProbeOutput(t *testing.T) {
	script := filepath.Join(t.TempDir(), "fake_probe_macos.py")
	err := os.WriteFile(script, []byte(`#!/usr/bin/env python3
import json
print(json.dumps({
  "platform_family": "macos",
  "mps_available": False,
  "preferred_device_type": "cpu",
  "ai_process_memory_bytes": 123456,
  "unavailable_reason": "PyTorch MPS backend is not available on this machine"
}))
`), 0o755)
	if err != nil {
		t.Fatalf("write fake probe script: %v", err)
	}

	probe := NewProbeService("python3", script)

	result, err := probe.Run(context.Background(), "macos")
	if err != nil {
		t.Fatalf("probe run failed: %v", err)
	}
	if result.PlatformFamily != "macos" {
		t.Fatalf("expected platform_family=macos, got %q", result.PlatformFamily)
	}
	if result.MPSAvailable != false {
		t.Fatalf("expected mps_available=false")
	}
	if result.PreferredDeviceType != "cpu" {
		t.Fatalf("expected preferred_device_type=cpu, got %q", result.PreferredDeviceType)
	}
	if result.AIProcessMemoryBytes != 123456 {
		t.Fatalf("expected ai_process_memory_bytes=123456, got %d", result.AIProcessMemoryBytes)
	}
	if result.UnavailableReason == "" {
		t.Fatalf("expected unavailable_reason to be parsed")
	}
}

func TestProbeServiceParsesWindowsProbeOutput(t *testing.T) {
	script := filepath.Join("testdata", "fake_probe_windows.py")
	probe := NewProbeService("python3", script)

	result, err := probe.Run(context.Background(), "windows")
	if err != nil {
		t.Fatalf("probe run failed: %v", err)
	}
	if result.PlatformFamily != "windows" {
		t.Fatalf("expected platform_family=windows, got %q", result.PlatformFamily)
	}
	if result.GPUName != "NVIDIA GeForce RTX 4060" {
		t.Fatalf("expected gpu_name preserved, got %q", result.GPUName)
	}
	if result.VRAMTotalMB != 8192 || result.VRAMUsedMB != 2048 {
		t.Fatalf("expected vram preserved, got total=%d used=%d", result.VRAMTotalMB, result.VRAMUsedMB)
	}
	if result.GPUUtilizationPercent != 33.5 {
		t.Fatalf("expected gpu_utilization_percent=33.5, got %v", result.GPUUtilizationPercent)
	}
	if result.TemperatureC != 61.5 {
		t.Fatalf("expected temperature_c=61.5, got %v", result.TemperatureC)
	}
}

func TestResolveProbePythonBinPrefersRepoVirtualEnv(t *testing.T) {
	repoRoot := t.TempDir()
	scriptPath := filepath.Join(repoRoot, "python-ai-service", "scripts", "monitor_probe.py")
	venvPython := filepath.Join(repoRoot, ".venv", "bin", "python")

	if err := os.MkdirAll(filepath.Dir(scriptPath), 0o755); err != nil {
		t.Fatalf("mkdir script dir: %v", err)
	}
	if err := os.WriteFile(scriptPath, []byte("print('ok')\n"), 0o644); err != nil {
		t.Fatalf("write script: %v", err)
	}
	if err := os.MkdirAll(filepath.Dir(venvPython), 0o755); err != nil {
		t.Fatalf("mkdir venv dir: %v", err)
	}
	if err := os.WriteFile(venvPython, []byte("#!/bin/sh\nexit 0\n"), 0o755); err != nil {
		t.Fatalf("write venv python: %v", err)
	}

	got := resolveProbePythonBin(scriptPath)

	if got != venvPython {
		t.Fatalf("expected repo virtualenv python %q, got %q", venvPython, got)
	}
}

func TestResolveProbePythonBinEnvOverrideWins(t *testing.T) {
	scriptPath := filepath.Join(t.TempDir(), "python-ai-service", "scripts", "monitor_probe.py")
	want := "/tmp/custom-monitor-probe-python"
	t.Setenv("MONITOR_PROBE_PYTHON_BIN", want)

	got := resolveProbePythonBin(scriptPath)

	if got != want {
		t.Fatalf("expected env override %q, got %q", want, got)
	}
}

func TestResolveMonitorProbeScriptPathFromRepoRootWorkingDirectory(t *testing.T) {
	repoRoot := t.TempDir()
	scriptPath := filepath.Join(repoRoot, "python-ai-service", "scripts", "monitor_probe.py")

	if err := os.MkdirAll(filepath.Dir(scriptPath), 0o755); err != nil {
		t.Fatalf("mkdir script dir: %v", err)
	}
	if err := os.WriteFile(scriptPath, []byte("print('ok')\n"), 0o644); err != nil {
		t.Fatalf("write script: %v", err)
	}

	wd, err := os.Getwd()
	if err != nil {
		t.Fatalf("getwd: %v", err)
	}
	if err := os.Chdir(repoRoot); err != nil {
		t.Fatalf("chdir repo root: %v", err)
	}
	t.Cleanup(func() {
		_ = os.Chdir(wd)
	})

	got := resolveMonitorProbeScriptPath()

	gotEval, err := filepath.EvalSymlinks(got)
	if err != nil {
		t.Fatalf("eval got path: %v", err)
	}
	wantEval, err := filepath.EvalSymlinks(scriptPath)
	if err != nil {
		t.Fatalf("eval expected path: %v", err)
	}

	if gotEval != wantEval {
		t.Fatalf("expected script path %q, got %q", wantEval, gotEval)
	}
}

func TestMatchesServiceProcessRecognizesCurrentPythonEntryPoints(t *testing.T) {
	text := "python -m uvicorn app.main:app --host 127.0.0.1 --port 8090"
	if !matchesProcessText(text, []string{"uvicorn app.main:app", "-m uvicorn app.main:app"}) {
		t.Fatalf("expected uvicorn command line to match current python-ai-service hints")
	}

	workerText := "python -m app.worker"
	if !matchesProcessText(workerText, []string{"-m app.worker", "app.worker"}) {
		t.Fatalf("expected app.worker command line to match current worker hints")
	}
}

func TestNormalizeProcessStatusTreatsSleepingProcessesAsRunning(t *testing.T) {
	for _, status := range []string{"idle", "sleep", "sleeping"} {
		if got := normalizeProcessStatus(status); got != "running" {
			t.Fatalf("expected %q to normalize to running, got %q", status, got)
		}
	}
}

func TestAlertServiceMarksMissingServiceAsCriticalAndAppendsAlert(t *testing.T) {
	ov := model.MonitorOverview{
		OverallHealth: "healthy",
		ServiceSnapshots: []model.ServiceSnapshot{
			{ServiceName: "python-ai-worker", Status: "missing"},
		},
	}

	got := NewAlertService().Evaluate(ov)

	if got.OverallHealth != "critical" {
		t.Fatalf("expected overall_health=critical, got %q", got.OverallHealth)
	}
	// AlertService builds alerts for all key services deterministically.
	if len(got.ActiveAlerts) != 3 {
		t.Fatalf("expected 3 active alerts (all key services), got %d", len(got.ActiveAlerts))
	}
	for _, a := range got.ActiveAlerts {
		if a.AlertID == "" || a.Level == "" || a.Message == "" {
			t.Fatalf("expected alert fields to be populated, got %+v", a)
		}
	}
}

func TestAlertServiceOnlyKeyServicesTriggerCritical(t *testing.T) {
	ov := model.MonitorOverview{
		OverallHealth: "healthy",
		ServiceSnapshots: []model.ServiceSnapshot{
			{ServiceName: "some-non-key-service", Status: "missing"},
		},
	}

	got := NewAlertService().Evaluate(ov)

	// Even though non-key is missing, key services are treated as missing by default -> critical.
	if got.OverallHealth != "critical" {
		t.Fatalf("expected overall_health=critical due to key service allowlist defaults, got %q", got.OverallHealth)
	}
	for _, a := range got.ActiveAlerts {
		if strings.HasPrefix(a.AlertID, "service:") && strings.Contains(a.AlertID, "some-non-key-service") {
			t.Fatalf("expected no service alert for non-key service, got %+v", a)
		}
	}
}

func TestAlertServiceEvaluateDoesNotDuplicateServiceAlerts(t *testing.T) {
	ov := model.MonitorOverview{
		OverallHealth: "healthy",
		ServiceSnapshots: []model.ServiceSnapshot{
			{ServiceName: "python-ai-worker", Status: "missing"},
		},
		ActiveAlerts: []model.MonitorAlert{
			{AlertID: "other:123", Level: "warning", Message: "preserve me"},
			{AlertID: "service:python-ai-worker", Level: "critical", Message: "old duplicate"},
		},
	}

	svc := NewAlertService()
	once := svc.Evaluate(ov)
	twice := svc.Evaluate(once)

	// other:* preserved, service:* rebuilt deterministically, no duplicates on repeated calls.
	countService := 0
	countOther := 0
	seen := map[string]bool{}
	for _, a := range twice.ActiveAlerts {
		if seen[a.AlertID] {
			t.Fatalf("unexpected duplicate alert_id=%q in %+v", a.AlertID, twice.ActiveAlerts)
		}
		seen[a.AlertID] = true
		if strings.HasPrefix(a.AlertID, "service:") {
			countService++
		} else {
			countOther++
		}
	}
	if countOther != 1 {
		t.Fatalf("expected 1 non-service alert preserved, got %d", countOther)
	}
	if countService != 3 {
		t.Fatalf("expected 3 service alerts (key services), got %d", countService)
	}
}

type fakeOverviewCollector struct {
	raw      RawSnapshot
	overview model.MonitorOverview

	collectCalls   int
	normalizeCalls int
}

func (f *fakeOverviewCollector) CollectCurrentSnapshot() RawSnapshot {
	f.collectCalls++
	return f.raw
}

func (f *fakeOverviewCollector) Normalize(raw RawSnapshot) model.MonitorOverview {
	f.normalizeCalls++
	return f.overview
}

func readNextSSEFrame(reader *bufio.Reader) (string, error) {
	var builder strings.Builder
	for {
		line, err := reader.ReadString('\n')
		if err != nil {
			if builder.Len() > 0 {
				return builder.String(), err
			}
			return "", err
		}
		builder.WriteString(line)
		if line == "\n" {
			return builder.String(), nil
		}
	}
}
