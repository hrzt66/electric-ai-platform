package repository

import (
	"context"
	"database/sql"
	"sync"

	"electric-ai/services/task-service/model"
)

type TaskRepository struct {
	db         *sql.DB
	schemaOnce sync.Once
	schemaErr  error
}

func NewTaskRepository(db *sql.DB) *TaskRepository {
	return &TaskRepository{db: db}
}

func (r *TaskRepository) ensureSchema(ctx context.Context) error {
	r.schemaOnce.Do(func() {
		const query = `
CREATE TABLE IF NOT EXISTS task_jobs (
	id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
	job_type VARCHAR(32) NOT NULL,
	status VARCHAR(32) NOT NULL,
	stage VARCHAR(32) NOT NULL,
	model_name VARCHAR(128) NOT NULL,
	prompt TEXT,
	negative_prompt TEXT,
	payload_json LONGTEXT NOT NULL,
	error_message TEXT,
	created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
	updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
)
`
		_, r.schemaErr = r.db.ExecContext(ctx, query)
	})
	return r.schemaErr
}

func (r *TaskRepository) Create(ctx context.Context, job model.Job) (model.Job, error) {
	if err := r.ensureSchema(ctx); err != nil {
		return model.Job{}, err
	}

	const query = `
INSERT INTO task_jobs (job_type, status, stage, model_name, prompt, negative_prompt, payload_json, error_message)
VALUES (?, ?, ?, ?, ?, ?, ?, ?)
`

	result, err := r.db.ExecContext(
		ctx,
		query,
		job.JobType,
		job.Status,
		job.Stage,
		job.ModelName,
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
SELECT id, job_type, status, stage, model_name, prompt, negative_prompt, payload_json, COALESCE(error_message, ''), created_at, updated_at
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

	const query = `
SELECT id, job_type, status, stage, model_name, prompt, negative_prompt, payload_json, COALESCE(error_message, ''), created_at, updated_at
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
