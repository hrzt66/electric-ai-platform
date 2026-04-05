package router

import (
	"net/http"

	"github.com/gin-gonic/gin"

	"electric-ai/services/model-service/controller"
	"electric-ai/services/platform-common/pkg/httpx"
)

func New(modelController *controller.ModelController) *gin.Engine {
	engine := gin.New()
	engine.Use(gin.Logger(), gin.Recovery())

	engine.GET("/health", func(ctx *gin.Context) {
		ctx.JSON(http.StatusOK, httpx.OK(gin.H{"status": "ok"}, "health"))
	})

	v1 := engine.Group("/api/v1")
	models := v1.Group("/models")
	models.GET("", modelController.ListActive)
	models.GET("/active", modelController.ListActive)

	return engine
}
