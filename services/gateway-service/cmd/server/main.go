package main

import (
	"log"
	"os"
	"path/filepath"
	"strings"

	"electric-ai/services/gateway-service/router"
	"electric-ai/services/gateway-service/service"
	"electric-ai/services/platform-common/pkg/config"
)

func main() {
	cfg, err := config.Load()
	if err != nil {
		log.Fatalf("load config failed: %v", err)
	}

	upstreams := router.Upstreams{
		Auth:        service.NewReverseProxy(getenv("AUTH_SERVICE_URL", "http://localhost:8081")),
		Model:       service.NewReverseProxy(getenv("MODEL_SERVICE_URL", "http://localhost:8082")),
		Task:        service.NewReverseProxy(getenv("TASK_SERVICE_URL", "http://localhost:8083")),
		Asset:       service.NewReverseProxy(getenv("ASSET_SERVICE_URL", "http://localhost:8084")),
		Audit:       service.NewReverseProxy(getenv("AUDIT_SERVICE_URL", "http://localhost:8085")),
		Files:       service.NewStaticFileHandler(getenv("IMAGE_OUTPUT_DIR", "model/image"), "/files/images/"),
		ImageChecks: service.NewStaticFileHandler(resolveImageCheckDir(), "/files/image-checks/"),
	}

	engine := router.New(upstreams)
	if err := engine.Run(":" + cfg.HTTPPort); err != nil {
		log.Fatalf("run server failed: %v", err)
	}
}

func getenv(key, fallback string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return fallback
}

func resolveImageCheckDir() string {
	if value := os.Getenv("IMAGE_CHECK_OUTPUT_DIR"); value != "" {
		return value
	}

	imageOutputDir := getenv("IMAGE_OUTPUT_DIR", "model/image")
	cleaned := filepath.Clean(imageOutputDir)
	suffix := string(filepath.Separator) + "image"
	if strings.HasSuffix(cleaned, suffix) {
		return strings.TrimSuffix(cleaned, suffix) + string(filepath.Separator) + "image_check"
	}
	return filepath.Join(filepath.Dir(cleaned), "image_check")
}
