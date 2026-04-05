package router

import (
	"net/http"

	"github.com/gin-gonic/gin"

	"electric-ai/services/asset-service/controller"
	"electric-ai/services/platform-common/pkg/httpx"
)

func New(assetController *controller.AssetController) *gin.Engine {
	engine := gin.New()
	engine.Use(gin.Logger(), gin.Recovery())

	engine.GET("/health", func(ctx *gin.Context) {
		ctx.JSON(http.StatusOK, httpx.OK(gin.H{"status": "ok"}, "health"))
	})

	v1 := engine.Group("/api/v1")
	assets := v1.Group("/assets")
	assets.POST("/results", assetController.SaveGenerateResult)

	return engine
}
