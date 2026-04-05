package controller

import (
	"net/http"
	"strconv"

	"github.com/gin-gonic/gin"

	"electric-ai/services/asset-service/model"
	"electric-ai/services/asset-service/service"
	"electric-ai/services/platform-common/pkg/httpx"
)

// AssetController 负责处理资产服务对外暴露的 HTTP 接口。
type AssetController struct {
	svc *service.AssetService
}

// NewAssetController 创建资产控制器实例。
func NewAssetController(svc *service.AssetService) *AssetController {
	return &AssetController{svc: svc}
}

// SaveGenerateResults 接收 Python 运行时回传的评分结果并写入资产表。
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

// ListHistory 返回历史中心展示所需的资产列表。
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

// GetAssetDetail 返回单个资产的详细信息，供历史详情抽屉展示。
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
