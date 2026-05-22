package router

import (
	"net/http"

	"github.com/gin-gonic/gin"

	"electric-ai/services/monitor-service/controller"
	"electric-ai/services/platform-common/pkg/httpx"
)

func New(monitorController *controller.MonitorController) *gin.Engine {
	engine := gin.New()
	engine.Use(gin.Logger(), gin.Recovery())

	engine.GET("/health", func(ctx *gin.Context) {
		ctx.JSON(http.StatusOK, httpx.OK(gin.H{"status": "ok"}, "health"))
	})

	v1 := engine.Group("/api/v1")
	monitor := v1.Group("/monitor")
	monitor.GET("/overview", monitorController.GetOverview)
	monitor.GET("/alerts", monitorController.GetAlerts)
	monitor.GET("/stream", monitorController.Stream)

	return engine
}

