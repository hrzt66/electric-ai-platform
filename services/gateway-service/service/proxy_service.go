package service

import (
	"net/http/httputil"
	"net/url"
)

func NewReverseProxy(target string) *httputil.ReverseProxy {
	parsed, _ := url.Parse(target)
	return httputil.NewSingleHostReverseProxy(parsed)
}
