package router

import (
	"net/http"
	"net/http/httputil"

	"github.com/gin-gonic/gin"

	"electric-ai/services/gateway-service/middleware"
)

type Upstreams struct {
	Auth  *httputil.ReverseProxy
	Model *httputil.ReverseProxy
	Task  *httputil.ReverseProxy
	Asset *httputil.ReverseProxy
	Audit *httputil.ReverseProxy
	Files http.Handler
}

func New(upstreams Upstreams) *gin.Engine {
	r := gin.Default()
	r.GET("/health", func(ctx *gin.Context) { ctx.JSON(200, gin.H{"status": "ok"}) })

	r.Any("/api/v1/auth/*path", gin.WrapH(upstreams.Auth))

	secured := r.Group("/")
	secured.Use(middleware.RequireBearer())
	secured.Any("/api/v1/models", gin.WrapH(upstreams.Model))
	secured.Any("/api/v1/models/*path", gin.WrapH(upstreams.Model))
	secured.Any("/api/v1/tasks", gin.WrapH(upstreams.Task))
	secured.Any("/api/v1/tasks/*path", gin.WrapH(upstreams.Task))
	secured.Any("/api/v1/assets", gin.WrapH(upstreams.Asset))
	secured.Any("/api/v1/assets/*path", gin.WrapH(upstreams.Asset))
	secured.Any("/api/v1/audit", gin.WrapH(upstreams.Audit))
	secured.Any("/api/v1/audit/*path", gin.WrapH(upstreams.Audit))

	r.Any("/files/images/*path", gin.WrapH(upstreams.Files))
	return r
}
