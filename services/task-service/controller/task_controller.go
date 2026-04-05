package controller

import (
	"net/http"

	"github.com/gin-gonic/gin"

	"electric-ai/services/platform-common/pkg/httpx"
	"electric-ai/services/task-service/model"
	"electric-ai/services/task-service/service"
)

type TaskController struct {
	svc *service.TaskService
}

func NewTaskController(svc *service.TaskService) *TaskController {
	return &TaskController{svc: svc}
}

func (c *TaskController) CreateGenerateJob(ctx *gin.Context) {
	var req model.CreateGenerateJobInput
	if err := ctx.ShouldBindJSON(&req); err != nil {
		ctx.JSON(http.StatusBadRequest, gin.H{
			"code":    1,
			"message": err.Error(),
		})
		return
	}

	job, err := c.svc.CreateGenerateJob(ctx.Request.Context(), req)
	if err != nil {
		ctx.JSON(http.StatusInternalServerError, gin.H{
			"code":    1,
			"message": err.Error(),
		})
		return
	}

	ctx.JSON(http.StatusOK, httpx.OK(job, "task-generate"))
}
