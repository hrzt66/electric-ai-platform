package controller

import (
	"net/http"
	"strconv"

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

func (c *AssetController) SaveGenerateResults(ctx *gin.Context) {
	var req model.SaveGenerateResultsInput
	if err := ctx.ShouldBindJSON(&req); err != nil {
		ctx.JSON(http.StatusBadRequest, gin.H{
			"code":    1,
			"message": err.Error(),
		})
		return
	}

	items, err := c.svc.SaveGenerateResults(ctx.Request.Context(), req)
	if err != nil {
		ctx.JSON(http.StatusInternalServerError, gin.H{
			"code":    1,
			"message": err.Error(),
		})
		return
	}

	ctx.JSON(http.StatusOK, httpx.OK(items, "asset-save"))
}

func (c *AssetController) ListHistory(ctx *gin.Context) {
	items, err := c.svc.ListHistory(ctx.Request.Context())
	if err != nil {
		ctx.JSON(http.StatusInternalServerError, gin.H{
			"code":    1,
			"message": err.Error(),
		})
		return
	}

	ctx.JSON(http.StatusOK, httpx.OK(items, "asset-history"))
}

func (c *AssetController) GetAssetDetail(ctx *gin.Context) {
	id, err := strconv.ParseInt(ctx.Param("id"), 10, 64)
	if err != nil {
		ctx.JSON(http.StatusBadRequest, gin.H{
			"code":    1,
			"message": "invalid asset id",
		})
		return
	}

	detail, err := c.svc.GetAssetDetail(ctx.Request.Context(), id)
	if err != nil {
		ctx.JSON(http.StatusInternalServerError, gin.H{
			"code":    1,
			"message": err.Error(),
		})
		return
	}

	ctx.JSON(http.StatusOK, httpx.OK(detail, "asset-detail"))
}
