package main

import (
	"log"
	"os"

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
		Auth:  service.NewReverseProxy(getenv("AUTH_SERVICE_URL", "http://localhost:8081")),
		Model: service.NewReverseProxy(getenv("MODEL_SERVICE_URL", "http://localhost:8082")),
		Task:  service.NewReverseProxy(getenv("TASK_SERVICE_URL", "http://localhost:8083")),
		Asset: service.NewReverseProxy(getenv("ASSET_SERVICE_URL", "http://localhost:8084")),
		Audit: service.NewReverseProxy(getenv("AUDIT_SERVICE_URL", "http://localhost:8085")),
		Files: service.NewStaticFileHandler(getenv("IMAGE_OUTPUT_DIR", `G:\electric-ai-runtime\outputs\images`), "/files/images/"),
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
