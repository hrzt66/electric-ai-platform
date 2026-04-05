package controller

import (
	"errors"
	"net/http"

	"github.com/gin-gonic/gin"

	"electric-ai/services/auth-service/model"
	"electric-ai/services/auth-service/service"
	"electric-ai/services/platform-common/pkg/httpx"
)

type AuthController struct {
	svc *service.AuthService
}

func NewAuthController(svc *service.AuthService) *AuthController {
	return &AuthController{svc: svc}
}

func (c *AuthController) Login(ctx *gin.Context) {
	var req model.LoginRequest
	if err := ctx.ShouldBindJSON(&req); err != nil {
		ctx.JSON(http.StatusBadRequest, gin.H{
			"code":    1,
			"message": err.Error(),
		})
		return
	}

	result, err := c.svc.Login(ctx.Request.Context(), req)
	if err != nil {
		statusCode := http.StatusInternalServerError
		if errors.Is(err, service.ErrInvalidCredentials) {
			statusCode = http.StatusUnauthorized
		}

		ctx.JSON(statusCode, gin.H{
			"code":    1,
			"message": err.Error(),
		})
		return
	}

	ctx.JSON(http.StatusOK, httpx.OK(result, "auth-login"))
}
