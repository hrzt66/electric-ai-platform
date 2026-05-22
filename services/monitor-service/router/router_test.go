package router_test

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/gin-gonic/gin"

	"electric-ai/services/monitor-service/controller"
	"electric-ai/services/monitor-service/model"
	"electric-ai/services/monitor-service/router"
	"electric-ai/services/monitor-service/service"
)

type httpxResponse[T any] struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
	Data    T      `json:"data"`
	TraceID string `json:"trace_id"`
}

func TestRouter_Health(t *testing.T) {
	gin.SetMode(gin.TestMode)

	fake := &service.FakeMonitorService{
		OverviewValue: model.MonitorOverview{OverallHealth: "healthy"},
		AlertsValue:   model.MonitorAlerts{ActiveAlerts: []model.MonitorAlert{}, RecentAlerts: []model.MonitorAlert{}},
		StreamEvents:  []string{"event: snapshot\ndata: {\"overall_health\":\"healthy\"}\n\n"},
	}
	engine := router.New(controller.NewMonitorController(fake))
	req := httptest.NewRequest(http.MethodGet, "/health", nil)
	rec := httptest.NewRecorder()
	engine.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected status %d, got %d. body=%s", http.StatusOK, rec.Code, rec.Body.String())
	}

	var got httpxResponse[map[string]any]
	if err := json.Unmarshal(rec.Body.Bytes(), &got); err != nil {
		t.Fatalf("expected JSON body, got err=%v body=%s", err, rec.Body.String())
	}
	if got.Code != 0 {
		t.Fatalf("expected code 0, got %d body=%s", got.Code, rec.Body.String())
	}
	if got.Data["status"] != "ok" {
		t.Fatalf("expected data.status=ok, got %v body=%s", got.Data["status"], rec.Body.String())
	}
}

func TestRouter_Overview(t *testing.T) {
	gin.SetMode(gin.TestMode)

	fake := &service.FakeMonitorService{
		OverviewValue: model.MonitorOverview{OverallHealth: "healthy"},
		AlertsValue:   model.MonitorAlerts{ActiveAlerts: []model.MonitorAlert{}, RecentAlerts: []model.MonitorAlert{}},
		StreamEvents:  []string{"event: snapshot\ndata: {\"overall_health\":\"healthy\"}\n\n"},
	}
	engine := router.New(controller.NewMonitorController(fake))
	req := httptest.NewRequest(http.MethodGet, "/api/v1/monitor/overview", nil)
	rec := httptest.NewRecorder()
	engine.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected status %d, got %d. body=%s", http.StatusOK, rec.Code, rec.Body.String())
	}

	var got httpxResponse[map[string]any]
	if err := json.Unmarshal(rec.Body.Bytes(), &got); err != nil {
		t.Fatalf("expected JSON body, got err=%v body=%s", err, rec.Body.String())
	}
	if got.Code != 0 {
		t.Fatalf("expected code 0, got %d body=%s", got.Code, rec.Body.String())
	}
	if got.Data["overall_health"] != "healthy" {
		t.Fatalf("expected data.overall_health=healthy, got %v body=%s", got.Data["overall_health"], rec.Body.String())
	}
}

func TestRouter_Alerts(t *testing.T) {
	gin.SetMode(gin.TestMode)

	fake := &service.FakeMonitorService{
		OverviewValue: model.MonitorOverview{OverallHealth: "healthy"},
		AlertsValue: model.MonitorAlerts{
			ActiveAlerts: []model.MonitorAlert{{AlertID: "a1", Level: "warning", Message: "cpu high"}},
			RecentAlerts: []model.MonitorAlert{},
		},
		StreamEvents: []string{"event: snapshot\ndata: {\"overall_health\":\"healthy\"}\n\n"},
	}
	engine := router.New(controller.NewMonitorController(fake))
	req := httptest.NewRequest(http.MethodGet, "/api/v1/monitor/alerts", nil)
	rec := httptest.NewRecorder()
	engine.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected status %d, got %d. body=%s", http.StatusOK, rec.Code, rec.Body.String())
	}

	var got httpxResponse[map[string]any]
	if err := json.Unmarshal(rec.Body.Bytes(), &got); err != nil {
		t.Fatalf("expected JSON body, got err=%v body=%s", err, rec.Body.String())
	}
	if got.Code != 0 {
		t.Fatalf("expected code 0, got %d body=%s", got.Code, rec.Body.String())
	}
	if _, ok := got.Data["active_alerts"]; !ok {
		t.Fatalf("expected data.active_alerts to exist body=%s", rec.Body.String())
	}
	if _, ok := got.Data["recent_alerts"]; !ok {
		t.Fatalf("expected data.recent_alerts to exist body=%s", rec.Body.String())
	}
}

func TestRouter_Stream(t *testing.T) {
	gin.SetMode(gin.TestMode)

	fake := &service.FakeMonitorService{
		OverviewValue: model.MonitorOverview{OverallHealth: "healthy"},
		AlertsValue:   model.MonitorAlerts{ActiveAlerts: []model.MonitorAlert{}, RecentAlerts: []model.MonitorAlert{}},
		// Task 4 expects SSE formatting to be produced by FormatSSE helper.
		StreamEvents: []string{"event: snapshot\ndata: {\"overall_health\":\"healthy\"}\n\n"},
	}
	engine := router.New(controller.NewMonitorController(fake))
	req := httptest.NewRequest(http.MethodGet, "/api/v1/monitor/stream", nil)
	rec := httptest.NewRecorder()
	engine.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected status %d, got %d. body=%s", http.StatusOK, rec.Code, rec.Body.String())
	}

	if ct := rec.Header().Get("Content-Type"); !strings.HasPrefix(ct, "text/event-stream") {
		t.Fatalf("expected Content-Type to start with text/event-stream, got %q body=%s", ct, rec.Body.String())
	}
	if !strings.Contains(rec.Body.String(), "event: snapshot") || !strings.Contains(rec.Body.String(), "overall_health") {
		t.Fatalf("expected SSE body to include snapshot event and overall_health, got body=%q", rec.Body.String())
	}
}

func TestRouter_Stream_UsesStandardSSEFormatting(t *testing.T) {
	gin.SetMode(gin.TestMode)

	fake := &service.FakeMonitorService{
		OverviewValue: model.MonitorOverview{OverallHealth: "healthy"},
		AlertsValue:   model.MonitorAlerts{ActiveAlerts: []model.MonitorAlert{}, RecentAlerts: []model.MonitorAlert{}},
		StreamEvents:  []string{service.FormatSSE("snapshot", []byte("{\"overall_health\":\"healthy\"}"))},
	}
	engine := router.New(controller.NewMonitorController(fake))
	req := httptest.NewRequest(http.MethodGet, "/api/v1/monitor/stream", nil)
	rec := httptest.NewRecorder()
	engine.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected status %d, got %d. body=%s", http.StatusOK, rec.Code, rec.Body.String())
	}
	if got := rec.Body.String(); got != "event: snapshot\ndata: {\"overall_health\":\"healthy\"}\n\n" {
		t.Fatalf("expected standard SSE body, got %q", got)
	}
}

func TestRouter_Overview_ServiceError_Envelope(t *testing.T) {
	gin.SetMode(gin.TestMode)

	fake := &service.FakeMonitorService{
		OverviewErr:  errBoom{},
		AlertsValue:  model.MonitorAlerts{ActiveAlerts: []model.MonitorAlert{}, RecentAlerts: []model.MonitorAlert{}},
		StreamEvents: []string{"event: snapshot\ndata: {\"overall_health\":\"healthy\"}\n\n"},
	}
	engine := router.New(controller.NewMonitorController(fake))
	req := httptest.NewRequest(http.MethodGet, "/api/v1/monitor/overview", nil)
	rec := httptest.NewRecorder()
	engine.ServeHTTP(rec, req)

	if rec.Code != http.StatusInternalServerError {
		t.Fatalf("expected status %d, got %d. body=%s", http.StatusInternalServerError, rec.Code, rec.Body.String())
	}

	var got httpxResponse[any]
	if err := json.Unmarshal(rec.Body.Bytes(), &got); err != nil {
		t.Fatalf("expected JSON body, got err=%v body=%s", err, rec.Body.String())
	}
	if got.Code == 0 {
		t.Fatalf("expected non-zero code on error, got %d body=%s", got.Code, rec.Body.String())
	}
	if got.TraceID == "" {
		t.Fatalf("expected trace_id to be set body=%s", rec.Body.String())
	}
}

type errBoom struct{}

func (errBoom) Error() string { return "boom" }
