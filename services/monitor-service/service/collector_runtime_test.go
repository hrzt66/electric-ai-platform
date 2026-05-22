package service

import (
	"runtime"
	"testing"
)

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
