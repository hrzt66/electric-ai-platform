package service

import (
	"io"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"testing"
)

func TestProxyForwardsRequestToUpstream(t *testing.T) {
	upstream := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		_, _ = io.WriteString(w, `{"ok":true}`)
	}))
	defer upstream.Close()

	proxy := NewReverseProxy(upstream.URL)
	rec := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodGet, "/health", nil)

	proxy.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rec.Code)
	}
}

func TestStaticFileHandlerServesImageDirectory(t *testing.T) {
	tempDir := t.TempDir()
	imagePath := filepath.Join(tempDir, "job-1.png")
	if err := os.WriteFile(imagePath, []byte("png-bytes"), 0o644); err != nil {
		t.Fatalf("write temp image: %v", err)
	}

	handler := NewStaticFileHandler(tempDir, "/files/images/")
	rec := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodGet, "/files/images/job-1.png", nil)

	handler.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rec.Code)
	}
	if rec.Body.String() != "png-bytes" {
		t.Fatalf("unexpected body: %s", rec.Body.String())
	}
}
