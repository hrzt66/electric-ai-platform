package main

import (
	"log"

	"electric-ai/services/monitor-service/controller"
	"electric-ai/services/monitor-service/router"
	"electric-ai/services/monitor-service/service"
	"electric-ai/services/platform-common/pkg/config"
)

func main() {
	cfg, err := config.Load()
	if err != nil {
		log.Fatalf("load config failed: %v", err)
	}

	monitorSvc := service.NewDefaultMonitorService()
	monitorController := controller.NewMonitorController(monitorSvc)
	engine := router.New(monitorController)
	if err := engine.Run(":" + cfg.HTTPPort); err != nil {
		log.Fatalf("run server failed: %v", err)
	}
}

