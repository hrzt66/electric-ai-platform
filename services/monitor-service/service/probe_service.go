package service

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"os/exec"
	"strings"
)

// ProbeResult is the cross-platform payload emitted by python-ai-service/scripts/monitor_probe.py.
// It is intentionally minimal and forward-compatible (unknown JSON fields are ignored).
type ProbeResult struct {
	PlatformFamily       string `json:"platform_family"`
	MPSAvailable         bool   `json:"mps_available"`
	PreferredDeviceType  string `json:"preferred_device_type"`
	AIProcessMemoryBytes uint64 `json:"ai_process_memory_bytes"`
	UnavailableReason    string `json:"unavailable_reason"`

	GPUName     string `json:"gpu_name"`
	VRAMTotalMB uint64 `json:"vram_total_mb"`
	VRAMUsedMB  uint64 `json:"vram_used_mb"`

	GPUUtilizationPercent float64 `json:"gpu_utilization_percent"`
	TemperatureC          float64 `json:"temperature_c"`
}

type ProbeService struct {
	pythonBin  string
	scriptPath string
}

func NewProbeService(pythonBin, scriptPath string) *ProbeService {
	return &ProbeService{pythonBin: pythonBin, scriptPath: scriptPath}
}

func (s *ProbeService) Run(ctx context.Context, platformFamily string) (ProbeResult, error) {
	// platformFamily is reserved for future args; keep signature aligned with the plan.
	_ = platformFamily

	cmd := exec.CommandContext(ctx, s.pythonBin, s.scriptPath)
	out, err := cmd.Output()
	if err != nil {
		// Try to attach stderr when possible to make failures debuggable.
		if ee, ok := err.(*exec.ExitError); ok {
			return ProbeResult{}, fmt.Errorf("probe failed: %w (stderr=%s)", err, strings.TrimSpace(string(ee.Stderr)))
		}
		return ProbeResult{}, fmt.Errorf("probe failed: %w", err)
	}

	out = bytes.TrimSpace(out)
	var result ProbeResult
	if err := json.Unmarshal(out, &result); err != nil {
		return ProbeResult{}, fmt.Errorf("probe output is not valid json: %w", err)
	}
	return result, nil
}
