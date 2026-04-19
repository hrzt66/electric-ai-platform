package router

import (
	"io"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
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

func TestImageCheckFilesAreServedWithoutAuthentication(t *testing.T) {
	tempDir := t.TempDir()
	imagePath := filepath.Join(tempDir, "job-1.png")
	if err := os.WriteFile(imagePath, []byte("checked-image"), 0o644); err != nil {
		t.Fatalf("write temp image: %v", err)
	}

	engine := New(Upstreams{
		Auth:  service.NewReverseProxy("http://example.com"),
		Model: service.NewReverseProxy("http://example.com"),
		Task:  service.NewReverseProxy("http://example.com"),
		Asset: service.NewReverseProxy("http://example.com"),
		Audit: service.NewReverseProxy("http://example.com"),
		Files: service.NewStaticFileHandler(tempDir, "/files/image-checks/"),
	})

	rec := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodGet, "/files/image-checks/job-1.png", nil)
	engine.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rec.Code)
	}
	if rec.Body.String() != "checked-image" {
		t.Fatalf("unexpected body: %s", rec.Body.String())
	}
}
