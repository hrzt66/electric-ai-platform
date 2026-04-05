package service

import (
	"net/http"
	"net/http/httputil"
	"net/url"
)

// NewReverseProxy 为网关内部各微服务构建统一反向代理。
func NewReverseProxy(target string) *httputil.ReverseProxy {
	parsed, _ := url.Parse(target)
	return httputil.NewSingleHostReverseProxy(parsed)
}

// NewStaticFileHandler 暴露生成图片目录，供前端通过网关统一访问。
func NewStaticFileHandler(root, prefix string) http.Handler {
	return http.StripPrefix(prefix, http.FileServer(http.Dir(root)))
}
