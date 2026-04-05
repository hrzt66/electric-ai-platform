package controller

import (
	"net/http"

	"github.com/gin-gonic/gin"

	"electric-ai/services/model-service/service"
	"electric-ai/services/platform-common/pkg/httpx"
)

type ModelController struct {
	svc *service.ModelService
}

func NewModelController(svc *service.ModelService) *ModelController {
	return &ModelController{svc: svc}
}

func (c *ModelController) ListActive(ctx *gin.Context) {
	items, err := c.svc.ListActive(ctx.Request.Context())
	if err != nil {
		ctx.JSON(http.StatusInternalServerError, gin.H{
			"code":    1,
			"message": err.Error(),
		})
		return
	}

	ctx.JSON(http.StatusOK, httpx.OK(items, "model-list"))
}
