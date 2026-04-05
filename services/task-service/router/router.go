package router

import (
	"net/http"

	"github.com/gin-gonic/gin"

	"electric-ai/services/platform-common/pkg/httpx"
	"electric-ai/services/task-service/controller"
)

func New(taskController *controller.TaskController) *gin.Engine {
	engine := gin.New()
	engine.Use(gin.Logger(), gin.Recovery())

	engine.GET("/health", func(ctx *gin.Context) {
		ctx.JSON(http.StatusOK, httpx.OK(gin.H{"status": "ok"}, "health"))
	})

	v1 := engine.Group("/api/v1")
	tasks := v1.Group("/tasks")
	tasks.POST("/generate", taskController.CreateGenerateJob)
	tasks.GET("", taskController.ListJobs)
	tasks.GET("/:id", taskController.GetJob)

	internal := engine.Group("/internal")
	internal.POST("/tasks/:id/status", taskController.UpdateTaskStatus)

	return engine
}
