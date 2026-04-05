package controller

import (
	"net/http"
	"strconv"

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

func (c *TaskController) GetJob(ctx *gin.Context) {
	id, err := strconv.ParseInt(ctx.Param("id"), 10, 64)
	if err != nil {
		ctx.JSON(http.StatusBadRequest, gin.H{
			"code":    1,
			"message": "invalid task id",
		})
		return
	}

	job, err := c.svc.GetJob(ctx.Request.Context(), id)
	if err != nil {
		ctx.JSON(http.StatusInternalServerError, gin.H{
			"code":    1,
			"message": err.Error(),
		})
		return
	}

	ctx.JSON(http.StatusOK, httpx.OK(job, "task-detail"))
}

func (c *TaskController) ListJobs(ctx *gin.Context) {
	jobs, err := c.svc.ListJobs(ctx.Request.Context())
	if err != nil {
		ctx.JSON(http.StatusInternalServerError, gin.H{
			"code":    1,
			"message": err.Error(),
		})
		return
	}

	ctx.JSON(http.StatusOK, httpx.OK(jobs, "task-list"))
}

func (c *TaskController) UpdateTaskStatus(ctx *gin.Context) {
	id, err := strconv.ParseInt(ctx.Param("id"), 10, 64)
	if err != nil {
		ctx.JSON(http.StatusBadRequest, gin.H{
			"code":    1,
			"message": "invalid task id",
		})
		return
	}

	var req model.UpdateJobStatusInput
	if err := ctx.ShouldBindJSON(&req); err != nil {
		ctx.JSON(http.StatusBadRequest, gin.H{
			"code":    1,
			"message": err.Error(),
		})
		return
	}

	job, err := c.svc.UpdateStatus(ctx.Request.Context(), id, req)
	if err != nil {
		ctx.JSON(http.StatusInternalServerError, gin.H{
			"code":    1,
			"message": err.Error(),
		})
		return
	}

	ctx.JSON(http.StatusOK, httpx.OK(job, "task-status"))
}
