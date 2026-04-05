package service

import (
	"context"

	"electric-ai/services/audit-service/model"
)

type TaskEvent = model.TaskEvent

type Repository interface {
	Append(ctx context.Context, item TaskEvent) error
}

type AuditService struct {
	repo Repository
}

func NewAuditService(repo Repository) *AuditService {
	return &AuditService{repo: repo}
}

func (s *AuditService) RecordTaskEvent(ctx context.Context, jobID int64, eventType, message string) error {
	return s.repo.Append(ctx, TaskEvent{
		JobID:     jobID,
		EventType: eventType,
		Message:   message,
	})
}
