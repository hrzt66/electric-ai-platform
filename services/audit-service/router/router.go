package router

import (
	"net/http"

	"github.com/gin-gonic/gin"

	"electric-ai/services/audit-service/controller"
	"electric-ai/services/platform-common/pkg/httpx"
)

func New(auditController *controller.AuditController) *gin.Engine {
	engine := gin.New()
	engine.Use(gin.Logger(), gin.Recovery())

	engine.GET("/health", func(ctx *gin.Context) {
		ctx.JSON(http.StatusOK, httpx.OK(gin.H{"status": "ok"}, "health"))
	})

	v1 := engine.Group("/api/v1")
	audit := v1.Group("/audit")
	audit.POST("/task-events", auditController.RecordTaskEvent)

	return engine
}
