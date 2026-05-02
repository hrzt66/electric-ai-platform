package middleware

import (
	"net/http"
	"strings"

	"github.com/gin-gonic/gin"
)

var defaultAllowedOrigins = map[string]struct{}{
	"https://www.camartshub.xyz":                       {},
	"https://electric-ai-platform-web-console.vercel.app": {},
}

func CORS() gin.HandlerFunc {
	return func(ctx *gin.Context) {
		origin := strings.TrimSpace(ctx.GetHeader("Origin"))
		if origin == "" {
			ctx.Next()
			return
		}

		if _, ok := defaultAllowedOrigins[origin]; !ok {
			ctx.Next()
			return
		}

		header := ctx.Writer.Header()
		header.Set("Access-Control-Allow-Origin", origin)
		header.Set("Access-Control-Allow-Credentials", "true")
		header.Set("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS")
		header.Set("Access-Control-Allow-Headers", "Authorization, Content-Type, Accept, Origin")
		header.Add("Vary", "Origin")
		header.Add("Vary", "Access-Control-Request-Method")
		header.Add("Vary", "Access-Control-Request-Headers")

		if ctx.Request.Method == http.MethodOptions {
			ctx.AbortWithStatus(http.StatusNoContent)
			return
		}

		ctx.Next()
	}
}
