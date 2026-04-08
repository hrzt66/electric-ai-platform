package repository

import (
	"context"
	"database/sql"
	"errors"
	"sync"

	mysqlDriver "github.com/go-sql-driver/mysql"

	"electric-ai/services/task-service/model"
)

type TaskRepository struct {
	db         *sql.DB
	schemaOnce sync.Once
	schemaErr  error
}

// NewTaskRepository 创建任务仓储，并在首次访问时按需补齐本地调试所需表结构。
func NewTaskRepository(db *sql.DB) *TaskRepository {
	return &TaskRepository{db: db}
}

// taskSchemaStatements 保存任务表的自举 SQL。
// 这里同时兼容全新数据库和从早期版本平滑升级的场景。
func taskSchemaStatements() []string {
	return []string{
		`
CREATE TABLE IF NOT EXISTS task_jobs (
	id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
	job_type VARCHAR(32) NOT NULL,
	status VARCHAR(32) NOT NULL,
	stage VARCHAR(32) NOT NULL,
	model_name VARCHAR(128) NOT NULL,
	scoring_model_name VARCHAR(128) NOT NULL DEFAULT 'electric-score-v1',
	prompt TEXT,
	negative_prompt TEXT,
	payload_json LONGTEXT NOT NULL,
	error_message TEXT,
	created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
	updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
)
`,
		`ALTER TABLE task_jobs ADD COLUMN stage VARCHAR(32) NOT NULL DEFAULT 'queued' AFTER status`,
		`ALTER TABLE task_jobs ADD COLUMN model_name VARCHAR(128) NOT NULL DEFAULT '' AFTER stage`,
		`ALTER TABLE task_jobs ADD COLUMN scoring_model_name VARCHAR(128) NOT NULL DEFAULT 'electric-score-v1' AFTER model_name`,
		`ALTER TABLE task_jobs ADD COLUMN prompt TEXT NULL AFTER scoring_model_name`,
		`ALTER TABLE task_jobs ADD COLUMN negative_prompt TEXT NULL AFTER prompt`,
		`ALTER TABLE task_jobs MODIFY COLUMN payload_json LONGTEXT NOT NULL`,
		`ALTER TABLE task_jobs ADD COLUMN error_message TEXT NULL AFTER payload_json`,
		`UPDATE task_jobs SET stage = status WHERE stage = 'queued' AND status <> 'queued'`,
	}
}

// ensureSchema 只在第一次调用时执行一次表结构补齐，避免每次请求重复迁移。
func (r *TaskRepository) ensureSchema(ctx context.Context) error {
	r.schemaOnce.Do(func() {
		for _, statement := range taskSchemaStatements() {
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

// isIgnorableMigrationError 用于忽略“列已存在”一类幂等迁移错误。
func isIgnorableMigrationError(err error) bool {
	var mysqlErr *mysqlDriver.MySQLError
	if !errors.As(err, &mysqlErr) {
		return false
	}
	return mysqlErr.Number == 1060
}

// TODO: 生产环境建议把这部分 schema bootstrap 收敛到独立迁移流程，服务启动阶段只做只读校验。

func (r *TaskRepository) Create(ctx context.Context, job model.Job) (model.Job, error) {
	if err := r.ensureSchema(ctx); err != nil {
		return model.Job{}, err
	}

	const query = `
INSERT INTO task_jobs (job_type, status, stage, model_name, scoring_model_name, prompt, negative_prompt, payload_json, error_message)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
`

	result, err := r.db.ExecContext(
		ctx,
		query,
		job.JobType,
		job.Status,
		job.Stage,
		job.ModelName,
		job.ScoringModelName,
		job.Prompt,
		job.NegativePrompt,
		job.PayloadJSON,
		job.ErrorMessage,
	)
	if err != nil {
		return model.Job{}, err
	}

	jobID, err := result.LastInsertId()
	if err != nil {
		return model.Job{}, err
	}

	job.ID = jobID
	return r.GetByID(ctx, jobID)
}

func (r *TaskRepository) GetByID(ctx context.Context, id int64) (model.Job, error) {
	if err := r.ensureSchema(ctx); err != nil {
		return model.Job{}, err
	}

	const query = `
SELECT id, job_type, status, stage, model_name, scoring_model_name, prompt, negative_prompt, payload_json, COALESCE(error_message, ''), created_at, updated_at
FROM task_jobs
WHERE id = ?
`

	var job model.Job
	if err := r.db.QueryRowContext(ctx, query, id).Scan(
		&job.ID,
		&job.JobType,
		&job.Status,
		&job.Stage,
		&job.ModelName,
		&job.ScoringModelName,
		&job.Prompt,
		&job.NegativePrompt,
		&job.PayloadJSON,
		&job.ErrorMessage,
		&job.CreatedAt,
		&job.UpdatedAt,
	); err != nil {
		return model.Job{}, err
	}
	return job, nil
}

func (r *TaskRepository) List(ctx context.Context) ([]model.Job, error) {
	if err := r.ensureSchema(ctx); err != nil {
		return nil, err
	}

	// 历史列表默认按最新任务倒序返回，满足前端工作台与审计页的主要浏览路径。
	const query = `
SELECT id, job_type, status, stage, model_name, scoring_model_name, prompt, negative_prompt, payload_json, COALESCE(error_message, ''), created_at, updated_at
FROM task_jobs
ORDER BY id DESC
LIMIT 50
`

	rows, err := r.db.QueryContext(ctx, query)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var jobs []model.Job
	for rows.Next() {
		var job model.Job
		if err := rows.Scan(
			&job.ID,
			&job.JobType,
			&job.Status,
			&job.Stage,
			&job.ModelName,
			&job.ScoringModelName,
			&job.Prompt,
			&job.NegativePrompt,
			&job.PayloadJSON,
			&job.ErrorMessage,
			&job.CreatedAt,
			&job.UpdatedAt,
		); err != nil {
			return nil, err
		}
		jobs = append(jobs, job)
	}

	return jobs, rows.Err()
}

func (r *TaskRepository) UpdateStatus(ctx context.Context, id int64, input model.UpdateJobStatusInput) (model.Job, error) {
	if err := r.ensureSchema(ctx); err != nil {
		return model.Job{}, err
	}

	const query = `
UPDATE task_jobs
SET status = ?, stage = ?, error_message = ?
WHERE id = ?
`

	if _, err := r.db.ExecContext(ctx, query, input.Status, input.Stage, input.ErrorMessage, id); err != nil {
		return model.Job{}, err
	}

	return r.GetByID(ctx, id)
}
