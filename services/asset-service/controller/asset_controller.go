package controller

import (
	"net/http"

	"github.com/gin-gonic/gin"

	"electric-ai/services/asset-service/model"
	"electric-ai/services/asset-service/service"
	"electric-ai/services/platform-common/pkg/httpx"
)

type AssetController struct {
	svc *service.AssetService
}

func NewAssetController(svc *service.AssetService) *AssetController {
	return &AssetController{svc: svc}
}

func (c *AssetController) SaveGenerateResult(ctx *gin.Context) {
	var req model.SaveGenerateResultInput
	if err := ctx.ShouldBindJSON(&req); err != nil {
		ctx.JSON(http.StatusBadRequest, gin.H{
			"code":    1,
			"message": err.Error(),
		})
		return
	}

	image, err := c.svc.SaveGenerateResult(ctx.Request.Context(), req)
	if err != nil {
		ctx.JSON(http.StatusInternalServerError, gin.H{
			"code":    1,
			"message": err.Error(),
		})
		return
	}

	ctx.JSON(http.StatusOK, httpx.OK(image, "asset-save"))
}
