package controller

import (
	"net/http"

	"github.com/gin-gonic/gin"

	"electric-ai/services/audit-service/service"
	"electric-ai/services/platform-common/pkg/httpx"
)

type RecordTaskEventRequest struct {
	JobID     int64  `json:"job_id" binding:"required"`
	EventType string `json:"event_type" binding:"required"`
	Message   string `json:"message" binding:"required"`
}

type AuditController struct {
	svc *service.AuditService
}

func NewAuditController(svc *service.AuditService) *AuditController {
	return &AuditController{svc: svc}
}

func (c *AuditController) RecordTaskEvent(ctx *gin.Context) {
	var req RecordTaskEventRequest
	if err := ctx.ShouldBindJSON(&req); err != nil {
		ctx.JSON(http.StatusBadRequest, gin.H{
			"code":    1,
			"message": err.Error(),
		})
		return
	}

	if err := c.svc.RecordTaskEvent(ctx.Request.Context(), req.JobID, req.EventType, req.Message); err != nil {
		ctx.JSON(http.StatusInternalServerError, gin.H{
			"code":    1,
			"message": err.Error(),
		})
		return
	}

	ctx.JSON(http.StatusOK, httpx.OK(gin.H{"status": "recorded"}, "audit-task-event"))
}
