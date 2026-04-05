package repository

import (
	"context"
	"database/sql"

	"electric-ai/services/audit-service/model"
)

type AuditRepository struct {
	db *sql.DB
}

func NewAuditRepository(db *sql.DB) *AuditRepository {
	return &AuditRepository{db: db}
}

func (r *AuditRepository) Append(ctx context.Context, item model.TaskEvent) error {
	_, err := r.db.ExecContext(ctx, `
INSERT INTO audit_task_events (job_id, event_type, message)
VALUES (?, ?, ?)
`, item.JobID, item.EventType, item.Message)
	return err
}
