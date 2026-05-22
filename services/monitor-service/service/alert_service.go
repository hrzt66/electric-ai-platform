package service

import (
	"sort"
	"strings"

	"electric-ai/services/monitor-service/model"
)

type AlertService struct{}

func NewAlertService() *AlertService { return &AlertService{} }

var keyServices = map[string]struct{}{
	"python-ai-service": {},
	"python-ai-worker":  {},
	"gateway-service":   {},
}

// Evaluate classifies service health into alerts and updates overall health.
// Rule (Task 3): any missing/non-running key service makes overall health critical.
func (s *AlertService) Evaluate(overview model.MonitorOverview) model.MonitorOverview {
	// Preserve existing non-service alerts; rebuild service:* alerts deterministically from snapshots.
	kept := make([]model.MonitorAlert, 0, len(overview.ActiveAlerts))
	for _, a := range overview.ActiveAlerts {
		if !strings.HasPrefix(a.AlertID, "service:") {
			kept = append(kept, a)
		}
	}

	// Index current statuses by service name (last write wins, but input should be stable).
	statusByService := map[string]string{}
	for _, snap := range overview.ServiceSnapshots {
		name := strings.TrimSpace(snap.ServiceName)
		if name == "" {
			continue
		}
		statusByService[name] = strings.ToLower(strings.TrimSpace(snap.Status))
	}

	// Evaluate allowlisted key services, including "missing" if not present in snapshots.
	serviceAlerts := make([]model.MonitorAlert, 0, len(keyServices))
	serviceNames := make([]string, 0, len(keyServices))
	for name := range keyServices {
		serviceNames = append(serviceNames, name)
	}
	sort.Strings(serviceNames)

	critical := strings.EqualFold(strings.TrimSpace(overview.OverallHealth), "critical")
	for _, name := range serviceNames {
		status, ok := statusByService[name]
		// Empty/unknown status is treated as non-running for key services.
		if !ok || status == "" || status != "running" {
			critical = true
			rawStatus := status
			if !ok {
				rawStatus = "missing"
			}
			serviceAlerts = append(serviceAlerts, model.MonitorAlert{
				AlertID: "service:" + name,
				Level:   "critical",
				Message: name + " not running (" + rawStatus + ")",
			})
		}
	}

	if critical {
		overview.OverallHealth = "critical"
	}
	extraAlerts, extraCritical, extraWarning := buildMacHealthAlerts(overview)
	if extraCritical {
		overview.OverallHealth = "critical"
	} else if !critical && extraWarning {
		overview.OverallHealth = "warning"
	}

	overview.ActiveAlerts = append(kept, serviceAlerts...)
	overview.ActiveAlerts = append(overview.ActiveAlerts, extraAlerts...)
	return overview
}

func buildMacHealthAlerts(overview model.MonitorOverview) ([]model.MonitorAlert, bool, bool) {
	alerts := make([]model.MonitorAlert, 0, 2)
	critical := false
	warning := false

	if overview.AcceleratorSnapshot != nil &&
		overview.AcceleratorSnapshot.AcceleratorType == "apple-mps" &&
		overview.AcceleratorSnapshot.Available != nil &&
		!*overview.AcceleratorSnapshot.Available &&
		hasRunningAIService(overview.ServiceSnapshots) {
		warning = true
		alerts = append(alerts, model.MonitorAlert{
			AlertID: "accelerator:mps-unavailable",
			Level:   "warning",
			Title:   "MPS 不可用",
			Message: overview.AcceleratorSnapshot.UnavailableReason,
		})
	}

	if overview.HostSnapshot != nil {
		switch strings.ToLower(strings.TrimSpace(overview.HostSnapshot.MemoryPressureLevel)) {
		case "critical":
			critical = true
			alerts = append(alerts, model.MonitorAlert{
				AlertID: "host:memory-pressure",
				Level:   "critical",
				Title:   "内存压力过高",
				Message: "memory pressure is critical",
			})
		case "warning":
			warning = true
			alerts = append(alerts, model.MonitorAlert{
				AlertID: "host:memory-pressure",
				Level:   "warning",
				Title:   "内存压力偏高",
				Message: "memory pressure is warning",
			})
		}

		if overview.HostSnapshot.SwapUsedBytes > 0 && overview.HostSnapshot.MemoryPressureLevel != "" {
			warning = true
			alerts = append(alerts, model.MonitorAlert{
				AlertID: "host:swap-pressure",
				Level:   "warning",
				Title:   "Swap 已启用",
				Message: "swap usage detected on host",
			})
		}
	}

	return alerts, critical, warning
}

func hasRunningAIService(snapshots []model.ServiceSnapshot) bool {
	for _, snap := range snapshots {
		name := strings.TrimSpace(snap.ServiceName)
		if name != "python-ai-service" && name != "python-ai-worker" {
			continue
		}
		if strings.EqualFold(strings.TrimSpace(snap.Status), "running") {
			return true
		}
	}
	return false
}
