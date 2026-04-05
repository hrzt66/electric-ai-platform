package repository

import (
	"context"
	"database/sql"
	"errors"
	"sync"

	mysqlDriver "github.com/go-sql-driver/mysql"

	"electric-ai/services/audit-service/model"
)

// AuditRepository 负责审计事件表的迁移和读写。
type AuditRepository struct {
	db         *sql.DB
	schemaOnce sync.Once
	schemaErr  error
}

// NewAuditRepository 创建审计仓储实例。
func NewAuditRepository(db *sql.DB) *AuditRepository {
	return &AuditRepository{db: db}
}

// auditSchemaStatements 返回审计表自举 SQL 与兼容升级 SQL。
func auditSchemaStatements() []string {
	return []string{
		`
CREATE TABLE IF NOT EXISTS audit_task_events (
	id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
	job_id BIGINT NOT NULL,
	event_type VARCHAR(128) NOT NULL,
	message TEXT,
	payload_json LONGTEXT,
	created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
)
`,
		`ALTER TABLE audit_task_events MODIFY COLUMN event_type VARCHAR(128) NOT NULL`,
		`ALTER TABLE audit_task_events MODIFY COLUMN message TEXT NULL`,
		`ALTER TABLE audit_task_events ADD COLUMN payload_json LONGTEXT NULL AFTER message`,
	}
}

// ensureSchema 确保审计表结构只在首次访问时初始化一次。
func (r *AuditRepository) ensureSchema(ctx context.Context) error {
	r.schemaOnce.Do(func() {
		for _, statement := range auditSchemaStatements() {
			if _, r.schemaErr = r.db.ExecContext(ctx, statement); r.schemaErr != nil {
				if isIgnorableMigrationError(r.schemaErr) {
					r.schemaErr = nil
					continue
				}
				return
			}
		}
	})
	return r.schemaErr
}

// isIgnorableMigrationError 用于忽略幂等迁移中的“列已存在”错误。
func isIgnorableMigrationError(err error) bool {
	var mysqlErr *mysqlDriver.MySQLError
	if !errors.As(err, &mysqlErr) {
		return false
	}
	return mysqlErr.Number == 1060
}

// Append 写入一条审计事件。
func (r *AuditRepository) Append(ctx context.Context, item model.TaskEvent) error {
	if err := r.ensureSchema(ctx); err != nil {
		return err
	}
	_, err := r.db.ExecContext(ctx, `
INSERT INTO audit_task_events (job_id, event_type, message, payload_json)
VALUES (?, ?, ?, ?)
`, item.JobID, item.EventType, item.Message, item.PayloadJSON)
	return err
}

// ListByJobID 查询某个任务的全部审计事件，按时间正序返回。
func (r *AuditRepository) ListByJobID(ctx context.Context, jobID int64) ([]model.TaskEvent, error) {
	if err := r.ensureSchema(ctx); err != nil {
		return nil, err
	}

	rows, err := r.db.QueryContext(ctx, `
SELECT id, job_id, event_type, message, COALESCE(payload_json, ''), created_at
FROM audit_task_events
WHERE job_id = ?
ORDER BY id ASC
`, jobID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var items []model.TaskEvent
	for rows.Next() {
		var item model.TaskEvent
		if err := rows.Scan(&item.ID, &item.JobID, &item.EventType, &item.Message, &item.PayloadJSON, &item.CreatedAt); err != nil {
			return nil, err
		}
		items = append(items, item)
	}
	return items, rows.Err()
}
