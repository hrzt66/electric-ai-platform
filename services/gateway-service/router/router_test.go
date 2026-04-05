package router

import (
	"io"
	"net/http"
	"net/http/httptest"
	"testing"

	"electric-ai/services/gateway-service/service"
)

func TestTasksIndexIsProxiedWithoutRedirect(t *testing.T) {
	taskUpstream := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/v1/tasks" {
			t.Fatalf("expected upstream path /api/v1/tasks, got %s", r.URL.Path)
		}
		w.WriteHeader(http.StatusOK)
		_, _ = io.WriteString(w, `{"code":0,"message":"success","data":[],"trace_id":"tasks"}`)
	}))
	defer taskUpstream.Close()

	engine := New(Upstreams{
		Auth:  service.NewReverseProxy(taskUpstream.URL),
		Model: service.NewReverseProxy(taskUpstream.URL),
		Task:  service.NewReverseProxy(taskUpstream.URL),
		Asset: service.NewReverseProxy(taskUpstream.URL),
		Audit: service.NewReverseProxy(taskUpstream.URL),
		Files: http.NotFoundHandler(),
	})
	gateway := httptest.NewServer(engine)
	defer gateway.Close()

	request, err := http.NewRequest(http.MethodGet, gateway.URL+"/api/v1/tasks", nil)
	if err != nil {
		t.Fatalf("new request: %v", err)
	}
	request.Header.Set("Authorization", "Bearer test-token")

	response, err := http.DefaultClient.Do(request)
	if err != nil {
		t.Fatalf("do request: %v", err)
	}
	defer response.Body.Close()
	body, err := io.ReadAll(response.Body)
	if err != nil {
		t.Fatalf("read body: %v", err)
	}

	if response.StatusCode != http.StatusOK {
		t.Fatalf("expected 200, got %d with body %s", response.StatusCode, string(body))
	}
}
