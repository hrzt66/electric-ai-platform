package service

import (
	"context"
	"encoding/json"
	"fmt"

	"electric-ai/services/audit-service/model"
)

type TaskEvent = model.TaskEvent
type RecordTaskEventInput = model.RecordTaskEventInput

// Repository 抽象审计事件存储，实现可以是 MySQL，也可以是后续的日志平台。
type Repository interface {
	Append(ctx context.Context, item TaskEvent) error
	ListByJobID(ctx context.Context, jobID int64) ([]TaskEvent, error)
}

// AuditService 负责把各微服务上报的事件规整为统一审计记录。
type AuditService struct {
	repo Repository
}

func NewAuditService(repo Repository) *AuditService {
	return &AuditService{repo: repo}
}

func (s *AuditService) RecordTaskEvent(ctx context.Context, input RecordTaskEventInput) error {
	// job_id 是审计时间线的主关联键，因此在写入前必须先校验并标准化。
	jobID, err := extractJobID(input.Payload["job_id"])
	if err != nil {
		return err
	}
	message, _ := input.Payload["message"].(string)
	payloadJSON, err := json.Marshal(input.Payload)
	if err != nil {
		return err
	}

	return s.repo.Append(ctx, TaskEvent{
		JobID:       jobID,
		EventType:   input.EventType,
		Message:     message,
		PayloadJSON: string(payloadJSON),
	})
}

func (s *AuditService) ListTaskEvents(ctx context.Context, jobID int64) ([]TaskEvent, error) {
	return s.repo.ListByJobID(ctx, jobID)
}

// extractJobID 兼容 JSON 反序列化后常见的几种数字类型。
func extractJobID(value any) (int64, error) {
	switch v := value.(type) {
	case int64:
		return v, nil
	case int:
		return int64(v), nil
	case float64:
		return int64(v), nil
	case json.Number:
		return v.Int64()
	default:
		return 0, fmt.Errorf("payload.job_id is required")
	}
}
