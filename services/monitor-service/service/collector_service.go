package service

import (
	"context"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"time"

	"electric-ai/services/monitor-service/model"
	"github.com/shirou/gopsutil/v4/cpu"
	"github.com/shirou/gopsutil/v4/disk"
	"github.com/shirou/gopsutil/v4/mem"
	"github.com/shirou/gopsutil/v4/process"
)

// RawSnapshot is the platform-specific collection output (pre-normalization).
// Keep it minimal and only include what's needed for normalization and tests.
type RawSnapshot struct {
	Platform   RawPlatform
	CapturedAt time.Time

	Host        RawHostSnapshot
	Services    []rawServiceSample
	Accelerator RawAcceleratorSnapshot
}

type RawPlatform struct {
	// OS is expected to be something like "darwin", "windows", "linux".
	OS string
}

type RawHostSnapshot struct {
	CPUUsagePercent float64

	MemoryTotalBytes uint64
	MemoryUsedBytes  uint64
	MemoryAvailBytes uint64

	SwapUsedBytes  uint64
	SwapTotalBytes uint64

	DiskTotalBytes uint64
	DiskUsedBytes  uint64
	DiskAvailBytes uint64

	MemoryPressureRaw string
}

type RawAcceleratorSnapshot struct {
	AppleMPS   *RawAppleMPSSnapshot
	NvidiaCUDA *RawNvidiaCUDASnapshot
}

type RawAppleMPSSnapshot struct {
	MPSAvailable          bool
	UnifiedMemoryPressure string
	AIProcessMemoryBytes  uint64
	PreferredDeviceType   string
	UnavailableReason     string
}

type RawNvidiaCUDASnapshot struct {
	Available             bool
	SummaryLabel          string
	GPUName               string
	VRAMTotalMB           int
	VRAMUsedMB            int
	GPUUtilizationPercent float64
	TemperatureC          float64
	UnavailableReason     string
}

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

type CollectorService struct{}

const probeNotCollectedYet = "probe not collected yet"

var keyServiceProcessHints = []struct {
	ServiceName string
	DisplayName string
	Hints       []string
}{
	{
		ServiceName: "gateway-service",
		DisplayName: "Gateway Service",
		Hints:       []string{"gateway-service", "services/gateway-service"},
	},
	{
		ServiceName: "python-ai-service",
		DisplayName: "Python AI Service",
		Hints: []string{
			"python-ai-service",
			"python-ai-service/app.py",
			"uvicorn app.main:app",
			"-m uvicorn app.main:app",
		},
	},
	{
		ServiceName: "python-ai-worker",
		DisplayName: "Python AI Worker",
		Hints: []string{
			"python-ai-worker",
			"python-ai-service/worker.py",
			"-m app.worker",
			"app.worker",
		},
	},
}

func (c *CollectorService) CollectCurrentSnapshot() RawSnapshot {
	now := time.Now().UTC()
	raw := RawSnapshot{
		Platform:   RawPlatform{OS: runtime.GOOS},
		CapturedAt: now,
	}

	raw.Host = c.collectHostSnapshot()
	raw.Services = c.collectServiceSamples()
	raw.Accelerator = c.collectPlatformAcceleratorPlaceholder(raw.Platform.OS)
	raw.Accelerator = c.enrichAcceleratorFromProbe(raw.Platform.OS, raw.Accelerator, raw.Host)

	return raw
}

// Normalize converts a raw, platform-specific snapshot into the normalized overview model.
func (c *CollectorService) Normalize(raw RawSnapshot) model.MonitorOverview {
	ov := model.MonitorOverview{
		OverallHealth:      "healthy",
		TaskRuntimeContext: model.TaskRuntimeContext{ActiveTaskCount: 0},
		ActiveAlerts:       []model.MonitorAlert{},
		RecentAlerts:       []model.MonitorAlert{},
	}

	host := normalizeHost(raw)
	acc := normalizeAccelerator(raw)
	ov.HostSnapshot = host
	ov.AcceleratorSnapshot = acc
	ov.ServiceSnapshots = c.normalizeServiceSnapshots(raw.Services)
	return ov
}

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

func deriveMemoryPressureLevel(host RawHostSnapshot) string {
	if host.MemoryTotalBytes == 0 {
		return ""
	}
	usedRatio := float64(host.MemoryUsedBytes) / float64(host.MemoryTotalBytes)
	switch {
	case usedRatio >= 0.9:
		return "critical"
	case usedRatio >= 0.75:
		return "warning"
	default:
		return "normal"
	}
}

func (c *CollectorService) collectServiceSamples() []rawServiceSample {
	procs, err := process.Processes()
	if err != nil {
		return nil
	}

	samples := make([]rawServiceSample, 0, len(keyServiceProcessHints))
	for _, meta := range keyServiceProcessHints {
		for _, procInfo := range procs {
			if procInfo == nil {
				continue
			}
			if !matchesServiceProcess(procInfo, meta.Hints) {
				continue
			}
			samples = append(samples, buildRawServiceSample(meta.ServiceName, meta.DisplayName, procInfo))
		}
	}
	return samples
}

func (c *CollectorService) collectPlatformAcceleratorPlaceholder(goos string) RawAcceleratorSnapshot {
	switch normalizePlatformFamily(goos) {
	case "macos":
		return RawAcceleratorSnapshot{
			AppleMPS: &RawAppleMPSSnapshot{
				MPSAvailable:          false,
				UnifiedMemoryPressure: "",
				AIProcessMemoryBytes:  0,
			},
		}
	case "windows":
		return RawAcceleratorSnapshot{
			NvidiaCUDA: &RawNvidiaCUDASnapshot{
				Available:         false,
				UnavailableReason: probeNotCollectedYet,
			},
		}
	default:
		return RawAcceleratorSnapshot{}
	}
}

func (c *CollectorService) enrichAcceleratorFromProbe(
	goos string,
	current RawAcceleratorSnapshot,
	host RawHostSnapshot,
) RawAcceleratorSnapshot {
	if normalizePlatformFamily(goos) != "macos" {
		return current
	}

	scriptPath := resolveMonitorProbeScriptPath()
	probe := NewProbeService(resolveProbePythonBin(scriptPath), scriptPath)
	result, err := probe.Run(context.Background(), "macos")
	if err != nil {
		if current.AppleMPS == nil {
			current.AppleMPS = &RawAppleMPSSnapshot{}
		}
		current.AppleMPS.UnavailableReason = strings.TrimSpace(err.Error())
		current.AppleMPS.UnifiedMemoryPressure = deriveMemoryPressureLevel(host)
		return current
	}

	current.AppleMPS = &RawAppleMPSSnapshot{
		MPSAvailable:          result.MPSAvailable,
		UnifiedMemoryPressure: deriveMemoryPressureLevel(host),
		AIProcessMemoryBytes:  result.AIProcessMemoryBytes,
		PreferredDeviceType:   strings.TrimSpace(result.PreferredDeviceType),
		UnavailableReason:     strings.TrimSpace(result.UnavailableReason),
	}
	return current
}

func resolveProbePythonBin(scriptPath string) string {
	if value := strings.TrimSpace(os.Getenv("MONITOR_PROBE_PYTHON_BIN")); value != "" {
		return value
	}

	if root := resolveRepoRootFromProbeScript(scriptPath); root != "" {
		candidates := []string{
			filepath.Join(root, ".venv", "bin", "python"),
			filepath.Join(root, "python-ai-service", ".venv", "bin", "python"),
		}
		for _, candidate := range candidates {
			if info, err := os.Stat(candidate); err == nil && !info.IsDir() && info.Mode()&0o111 != 0 {
				return candidate
			}
		}
	}

	return "python3"
}

func resolveRepoRootFromProbeScript(scriptPath string) string {
	cleaned := filepath.Clean(strings.TrimSpace(scriptPath))
	if cleaned == "" {
		return ""
	}

	scriptDir := filepath.Dir(cleaned)
	if filepath.Base(scriptDir) != "scripts" {
		return ""
	}
	serviceDir := filepath.Dir(scriptDir)
	if filepath.Base(serviceDir) != "python-ai-service" {
		return ""
	}
	return filepath.Dir(serviceDir)
}

func resolveMonitorProbeScriptPath() string {
	if value := strings.TrimSpace(os.Getenv("MONITOR_PROBE_SCRIPT")); value != "" {
		return value
	}

	wd, err := os.Getwd()
	if err != nil {
		return filepath.Join("..", "..", "python-ai-service", "scripts", "monitor_probe.py")
	}

	candidates := []string{
		filepath.Join(wd, "python-ai-service", "scripts", "monitor_probe.py"),
		filepath.Join(wd, "..", "..", "python-ai-service", "scripts", "monitor_probe.py"),
	}
	for _, candidate := range candidates {
		cleaned := filepath.Clean(candidate)
		if info, statErr := os.Stat(cleaned); statErr == nil && !info.IsDir() {
			return cleaned
		}
	}

	return filepath.Clean(candidates[0])
}

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
			ServiceName: sample.ServiceName,
			DisplayName: sample.DisplayName,
			PID:         sample.PID,
			Status:      sample.Status,
			UptimeSeconds:       sample.UptimeSeconds,
			CPUPercent:          sample.CPUPercent,
			ResidentMemoryBytes: sample.ResidentMemoryBytes,
			SampleOK:            sample.SampleOK,
			SampleError:         sample.SampleError,
		})
	}
	return rows
}

func matchesServiceProcess(procInfo *process.Process, hints []string) bool {
	name, _ := procInfo.Name()
	exe, _ := procInfo.Exe()
	cmd, _ := procInfo.Cmdline()
	return matchesProcessText(strings.Join([]string{name, exe, cmd}, " "), hints)
}

func matchesProcessText(text string, hints []string) bool {
	lowerText := strings.ToLower(strings.TrimSpace(text))
	if lowerText == "" {
		return false
	}
	for _, hint := range hints {
		if hint == "" {
			continue
		}
		if strings.Contains(lowerText, strings.ToLower(hint)) {
			return true
		}
	}
	return false
}

func buildRawServiceSample(serviceName, displayName string, procInfo *process.Process) rawServiceSample {
	sample := rawServiceSample{
		ServiceName: serviceName,
		DisplayName: displayName,
		Status:      "running",
		SampleOK:    true,
	}

	if procInfo == nil {
		sample.Status = "missing"
		sample.SampleOK = false
		sample.SampleError = "process handle missing"
		return sample
	}

	sample.PID = procInfo.Pid

	if memInfo, err := procInfo.MemoryInfo(); err == nil && memInfo != nil {
		sample.ResidentMemoryBytes = memInfo.RSS
	}

	if cpuPercent, err := procInfo.CPUPercent(); err == nil {
		sample.CPUPercent = cpuPercent
	}

	if createTimeMs, err := procInfo.CreateTime(); err == nil && createTimeMs > 0 {
		sample.UptimeSeconds = int64(time.Since(time.UnixMilli(createTimeMs)).Seconds())
		if sample.UptimeSeconds < 0 {
			sample.UptimeSeconds = 0
		}
	}

	if statuses, err := procInfo.Status(); err == nil && len(statuses) > 0 {
		sample.Status = normalizeProcessStatus(statuses[0])
	}

	return sample
}

func normalizeProcessStatus(status string) string {
	state := strings.ToLower(strings.TrimSpace(status))
	switch state {
	case "", "running", "run":
		return "running"
	case "idle", "sleep", "sleeping":
		return "running"
	case "stop", "stopped", "zombie", "dead":
		return "stopped"
	default:
		return state
	}
}

func normalizeHost(raw RawSnapshot) *model.HostSnapshot {
	hs := &model.HostSnapshot{
		PlatformFamily:      normalizePlatformFamily(raw.Platform.OS),
		CPUUsagePercent:     raw.Host.CPUUsagePercent,
		MemoryTotalBytes:    raw.Host.MemoryTotalBytes,
		MemoryUsedBytes:     raw.Host.MemoryUsedBytes,
		SwapUsedBytes:       raw.Host.SwapUsedBytes,
		SwapTotalBytes:      raw.Host.SwapTotalBytes,
		DiskTotalBytes:      raw.Host.DiskTotalBytes,
		DiskUsedBytes:       raw.Host.DiskUsedBytes,
		MemoryPressureLevel: strings.TrimSpace(raw.Host.MemoryPressureRaw),
	}

	// CapturedAt is optional; if zero, leave nil.
	if !raw.CapturedAt.IsZero() {
		t := raw.CapturedAt
		hs.CapturedAt = &t
	}

	// Derive available bytes if not provided.
	if raw.Host.MemoryAvailBytes != 0 {
		hs.MemoryAvailableBytes = raw.Host.MemoryAvailBytes
	} else if raw.Host.MemoryTotalBytes >= raw.Host.MemoryUsedBytes {
		hs.MemoryAvailableBytes = raw.Host.MemoryTotalBytes - raw.Host.MemoryUsedBytes
	}

	if raw.Host.DiskAvailBytes != 0 {
		hs.DiskAvailableBytes = raw.Host.DiskAvailBytes
	} else if raw.Host.DiskTotalBytes >= raw.Host.DiskUsedBytes {
		hs.DiskAvailableBytes = raw.Host.DiskTotalBytes - raw.Host.DiskUsedBytes
	}

	return hs
}

func normalizeAccelerator(raw RawSnapshot) *model.AcceleratorSnapshot {
	if raw.Accelerator.AppleMPS != nil || normalizePlatformFamily(raw.Platform.OS) == "macos" {
		if raw.Accelerator.AppleMPS == nil {
			// Platform says macOS but no collector data; still emit normalized type.
			avail := false
			return &model.AcceleratorSnapshot{
				AcceleratorType:   "apple-mps",
				Available:         &avail,
				UnavailableReason: probeNotCollectedYet,
			}
		}
		mps := raw.Accelerator.AppleMPS
		avail := mps.MPSAvailable
		// For Task 2 "current snapshot" semantics: if we haven't probed yet, do not imply availability.
		reason := strings.TrimSpace(mps.UnavailableReason)
		if !avail && reason == "" {
			reason = probeNotCollectedYet
		}
		mem := mps.AIProcessMemoryBytes
		return &model.AcceleratorSnapshot{
			AcceleratorType:       "apple-mps",
			Available:             &avail,
			MPSAvailable:          &avail,
			UnifiedMemoryPressure: mps.UnifiedMemoryPressure,
			AIProcessMemoryBytes:  &mem,
			UnavailableReason:     reason,
			PreferredDeviceType:   strings.TrimSpace(mps.PreferredDeviceType),
		}
	}

	if raw.Accelerator.NvidiaCUDA != nil || normalizePlatformFamily(raw.Platform.OS) == "windows" {
		if raw.Accelerator.NvidiaCUDA == nil {
			avail := false
			return &model.AcceleratorSnapshot{
				AcceleratorType:   "nvidia-cuda",
				Available:         &avail,
				UnavailableReason: probeNotCollectedYet,
			}
		}
		cuda := raw.Accelerator.NvidiaCUDA
		avail := cuda.Available
		reason := strings.TrimSpace(cuda.UnavailableReason)
		if !avail && reason == "" {
			reason = probeNotCollectedYet
		}
		return &model.AcceleratorSnapshot{
			AcceleratorType:       "nvidia-cuda",
			Available:             &avail,
			SummaryLabel:          cuda.SummaryLabel,
			GPUName:               cuda.GPUName,
			VRAMTotalMB:           cuda.VRAMTotalMB,
			VRAMUsedMB:            cuda.VRAMUsedMB,
			GPUUtilizationPercent: cuda.GPUUtilizationPercent,
			TemperatureC:          cuda.TemperatureC,
			UnavailableReason:     reason,
		}
	}

	// Unknown/no accelerator data.
	return nil
}

func normalizePlatformFamily(os string) string {
	switch strings.ToLower(strings.TrimSpace(os)) {
	case "darwin", "mac", "macos", "osx":
		return "macos"
	case "windows", "win32":
		return "windows"
	case "linux":
		return "linux"
	default:
		return ""
	}
}
