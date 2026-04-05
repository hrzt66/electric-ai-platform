package controller

import (
	"net/http"

	"github.com/gin-gonic/gin"

	"electric-ai/services/model-service/service"
	"electric-ai/services/platform-common/pkg/httpx"
)

// ModelController 负责模型目录相关 HTTP 接口。
type ModelController struct {
	svc *service.ModelService
}

// NewModelController 创建模型控制器实例。
func NewModelController(svc *service.ModelService) *ModelController {
	return &ModelController{svc: svc}
}

// ListModels 返回模型中心展示所需的全部模型条目。
func (c *ModelController) ListModels(ctx *gin.Context) {
	items, err := c.svc.ListModels(ctx.Request.Context())
	if err != nil {
		ctx.JSON(http.StatusInternalServerError, gin.H{
			"code":    1,
			"message": err.Error(),
		})
		return
	}

	ctx.JSON(http.StatusOK, httpx.OK(items, "model-list"))
}

// GetModel 返回指定模型的详细信息。
func (c *ModelController) GetModel(ctx *gin.Context) {
	item, err := c.svc.GetModel(ctx.Request.Context(), ctx.Param("name"))
	if err != nil {
		ctx.JSON(http.StatusInternalServerError, gin.H{
			"code":    1,
			"message": err.Error(),
		})
		return
	}

	ctx.JSON(http.StatusOK, httpx.OK(item, "model-detail"))
}
