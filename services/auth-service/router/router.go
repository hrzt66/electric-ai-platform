package router

import (
	"net/http"

	"github.com/gin-gonic/gin"

	"electric-ai/services/auth-service/controller"
	"electric-ai/services/platform-common/pkg/httpx"
)

func New(authController *controller.AuthController) *gin.Engine {
	engine := gin.New()
	engine.Use(gin.Logger(), gin.Recovery())

	engine.GET("/health", func(ctx *gin.Context) {
		ctx.JSON(http.StatusOK, httpx.OK(gin.H{"status": "ok"}, "health"))
	})

	v1 := engine.Group("/api/v1")
	auth := v1.Group("/auth")
	auth.POST("/login", authController.Login)

	return engine
}
