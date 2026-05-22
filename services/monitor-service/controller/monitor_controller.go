package controller

import (
	"context"
	"io"
	"net/http"

	"github.com/gin-gonic/gin"

	"electric-ai/services/monitor-service/service"
	"electric-ai/services/platform-common/pkg/httpx"
)

type MonitorController struct {
	svc service.MonitorService
}

func NewMonitorController(svc service.MonitorService) *MonitorController {
	return &MonitorController{svc: svc}
}

type errorData struct{}

func writeError(ctx *gin.Context, status int, traceID string, err error) {
	msg := "internal error"
	if err != nil {
		msg = err.Error()
	}
	resp := httpx.Response[errorData]{Code: 1, Message: msg, Data: errorData{}, TraceID: traceID}
	ctx.JSON(status, resp)
}

func (c *MonitorController) GetOverview(ctx *gin.Context) {
	overview, err := c.svc.GetOverview(ctx.Request.Context())
	if err != nil {
		writeError(ctx, http.StatusInternalServerError, "monitor-overview", err)
		return
	}
	ctx.JSON(http.StatusOK, httpx.OK(overview, "monitor-overview"))
}

func (c *MonitorController) GetAlerts(ctx *gin.Context) {
	alerts, err := c.svc.GetAlerts(ctx.Request.Context())
	if err != nil {
		writeError(ctx, http.StatusInternalServerError, "monitor-alerts", err)
		return
	}
	ctx.JSON(http.StatusOK, httpx.OK(alerts, "monitor-alerts"))
}

func (c *MonitorController) Stream(ctx *gin.Context) {
	reader, err := c.svc.Stream(ctx.Request.Context())
	if err != nil {
		writeError(ctx, http.StatusInternalServerError, "monitor-stream", err)
		return
	}

	ctx.Header("Content-Type", "text/event-stream")
	ctx.Header("Cache-Control", "no-cache")
	ctx.Header("Connection", "keep-alive")
	ctx.Status(http.StatusOK)

	// If supported, flush headers immediately so clients can establish EventSource promptly.
	f, canFlush := ctx.Writer.(http.Flusher)
	if canFlush {
		f.Flush()
	}

	// Avoid scanner framing: stream raw bytes. When flushing is supported, flush after each write.
	dst := io.Writer(ctx.Writer)
	if canFlush {
		dst = &flushingWriter{w: ctx.Writer, f: f, ctx: ctx.Request.Context()}
	}

	_, err = io.Copy(dst, reader)
	if ctx.Request.Context().Err() != nil {
		return
	}
	if err != nil {
		// Client disconnects or canceled contexts shouldn't panic. If response already started,
		// there's nothing reasonable to write back.
		return
	}
}

type flushingWriter struct {
	w   io.Writer
	f   http.Flusher
	ctx context.Context
}

func (fw *flushingWriter) Write(p []byte) (int, error) {
	if fw.ctx != nil && fw.ctx.Err() != nil {
		return 0, fw.ctx.Err()
	}
	n, err := fw.w.Write(p)
	fw.f.Flush()
	return n, err
}
