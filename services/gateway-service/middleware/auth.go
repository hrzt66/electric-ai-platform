package middleware

import (
	"net/http"
	"strings"

	"github.com/gin-gonic/gin"
)

func RequireBearer() gin.HandlerFunc {
	return func(ctx *gin.Context) {
		if strings.TrimSpace(ctx.GetHeader("Authorization")) == "" {
			ctx.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"message": "missing authorization"})
			return
		}
		ctx.Next()
	}
}
