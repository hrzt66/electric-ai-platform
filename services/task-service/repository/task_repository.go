package repository

import (
	"context"
	"database/sql"

	"electric-ai/services/task-service/model"
)

type TaskRepository struct {
	db *sql.DB
}

func NewTaskRepository(db *sql.DB) *TaskRepository {
	return &TaskRepository{db: db}
}

func (r *TaskRepository) Create(ctx context.Context, job model.Job) (model.Job, error) {
	const query = `
INSERT INTO task_jobs (job_type, status, payload_json)
VALUES (?, ?, ?)
`

	result, err := r.db.ExecContext(ctx, query, job.JobType, job.Status, job.PayloadJSON)
	if err != nil {
		return model.Job{}, err
	}

	jobID, err := result.LastInsertId()
	if err != nil {
		return model.Job{}, err
	}

	job.ID = jobID
	return job, nil
}
