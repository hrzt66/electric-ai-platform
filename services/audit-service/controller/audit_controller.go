package controller

import (
	"net/http"
	"strconv"

	"github.com/gin-gonic/gin"

	"electric-ai/services/audit-service/model"
	"electric-ai/services/audit-service/service"
	"electric-ai/services/platform-common/pkg/httpx"
)

// AuditController 负责任务审计事件的写入与查询接口。
type AuditController struct {
	svc *service.AuditService
}

// NewAuditController 创建审计控制器实例。
func NewAuditController(svc *service.AuditService) *AuditController {
	return &AuditController{svc: svc}
}

// RecordTaskEvent 接收任务事件并写入审计表。
func (c *AuditController) RecordTaskEvent(ctx *gin.Context) {
	var req model.RecordTaskEventInput
	if err := ctx.ShouldBindJSON(&req); err != nil {
		ctx.JSON(http.StatusBadRequest, gin.H{
			"code":    1,
			"message": err.Error(),
		})
		return
	}

	if err := c.svc.RecordTaskEvent(ctx.Request.Context(), req); err != nil {
		ctx.JSON(http.StatusInternalServerError, gin.H{
			"code":    1,
			"message": err.Error(),
		})
		return
	}

	ctx.JSON(http.StatusOK, httpx.OK(gin.H{"status": "recorded"}, "audit-task-event"))
}

// ListTaskEvents 按任务 ID 返回时间线事件列表。
func (c *AuditController) ListTaskEvents(ctx *gin.Context) {
	jobID, err := strconv.ParseInt(ctx.Param("job_id"), 10, 64)
	if err != nil {
		ctx.JSON(http.StatusBadRequest, gin.H{
			"code":    1,
			"message": "invalid task id",
		})
		return
	}

	items, err := c.svc.ListTaskEvents(ctx.Request.Context(), jobID)
	if err != nil {
		ctx.JSON(http.StatusInternalServerError, gin.H{
			"code":    1,
			"message": err.Error(),
		})
		return
	}

	ctx.JSON(http.StatusOK, httpx.OK(items, "audit-task-list"))
}
