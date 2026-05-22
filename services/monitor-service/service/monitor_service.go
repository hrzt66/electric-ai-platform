package service

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"strings"
	"time"

	"electric-ai/services/monitor-service/model"
)

type overviewCollector interface {
	CollectCurrentSnapshot() RawSnapshot
	Normalize(raw RawSnapshot) model.MonitorOverview
}

type MonitorService interface {
	GetOverview(ctx context.Context) (model.MonitorOverview, error)
	GetAlerts(ctx context.Context) (model.MonitorAlerts, error)
	Stream(ctx context.Context) (io.Reader, error)
}

type DefaultMonitorService struct {
	collector overviewCollector
}

func NewDefaultMonitorService() *DefaultMonitorService {
	return &DefaultMonitorService{collector: &CollectorService{}}
}

func NewDefaultMonitorServiceWithCollector(collector overviewCollector) *DefaultMonitorService {
	return &DefaultMonitorService{collector: collector}
}

func (s *DefaultMonitorService) buildOverview(ctx context.Context) (model.MonitorOverview, error) {
	raw := s.collector.CollectCurrentSnapshot()
	ov := s.collector.Normalize(raw)
	ov = NewAlertService().Evaluate(ov)
	ov.ActiveAlerts = ensureAlerts(ov.ActiveAlerts)
	ov.RecentAlerts = ensureRecentAlerts(ov.RecentAlerts)
	return ov, nil
}

func (s *DefaultMonitorService) GetOverview(ctx context.Context) (model.MonitorOverview, error) {
	return s.buildOverview(ctx)
}

func (s *DefaultMonitorService) GetAlerts(ctx context.Context) (model.MonitorAlerts, error) {
	overview, err := s.GetOverview(ctx)
	if err != nil {
		return model.MonitorAlerts{}, err
	}
	return model.MonitorAlerts{
		ActiveAlerts: ensureAlerts(overview.ActiveAlerts),
		RecentAlerts: ensureRecentAlerts(overview.RecentAlerts),
	}, nil
}

func (s *DefaultMonitorService) Stream(ctx context.Context) (io.Reader, error) {
	pr, pw := io.Pipe()
	go func() {
		ticker := time.NewTicker(1 * time.Second)
		defer ticker.Stop()
		defer pw.Close()

		writeSnapshot := func() error {
			overview, err := s.buildOverview(ctx)
			if err != nil {
				return err
			}
			payload, err := json.Marshal(overview)
			if err != nil {
				return fmt.Errorf("marshal monitor overview for sse: %w", err)
			}
			if _, err := io.WriteString(pw, FormatSSE("snapshot", payload)); err != nil {
				return err
			}
			return nil
		}

		// Emit first frame immediately so clients get data as soon as they connect.
		if err := writeSnapshot(); err != nil {
			_ = pw.CloseWithError(err)
			return
		}

		for {
			select {
			case <-ctx.Done():
				_ = pw.CloseWithError(ctx.Err())
				return
			case <-ticker.C:
				if err := writeSnapshot(); err != nil {
					_ = pw.CloseWithError(err)
					return
				}
			}
		}
	}()
	return pr, nil
}

// FakeMonitorService is used in tests.
type FakeMonitorService struct {
	OverviewValue model.MonitorOverview
	AlertsValue   model.MonitorAlerts
	StreamEvents  []string

	OverviewErr error
	AlertsErr   error
	StreamErr   error
}

func (f *FakeMonitorService) GetOverview(ctx context.Context) (model.MonitorOverview, error) {
	if f.OverviewErr != nil {
		return model.MonitorOverview{}, f.OverviewErr
	}
	return f.OverviewValue, nil
}

func (f *FakeMonitorService) GetAlerts(ctx context.Context) (model.MonitorAlerts, error) {
	if f.AlertsErr != nil {
		return model.MonitorAlerts{}, f.AlertsErr
	}
	return f.AlertsValue, nil
}

func (f *FakeMonitorService) Stream(ctx context.Context) (io.Reader, error) {
	if f.StreamErr != nil {
		return nil, f.StreamErr
	}
	return strings.NewReader(strings.Join(f.StreamEvents, "")), nil
}

func ensureAlerts(alerts []model.MonitorAlert) []model.MonitorAlert {
	if alerts == nil {
		return []model.MonitorAlert{}
	}
	return alerts
}

func ensureRecentAlerts(alerts []model.MonitorAlert) []model.MonitorAlert {
	if alerts == nil {
		return []model.MonitorAlert{}
	}
	return alerts
}
