package service

import (
	"context"
	"encoding/json"

	"github.com/redis/go-redis/v9"

	"electric-ai/services/task-service/model"
)

type Job = model.Job
type CreateGenerateJobInput = model.CreateGenerateJobInput

type Repository interface {
	Create(ctx context.Context, job Job) (Job, error)
}

type TaskService struct {
	repo Repository
	rdb  *redis.Client
}

func NewTaskService(repo Repository, rdb *redis.Client) *TaskService {
	return &TaskService{repo: repo, rdb: rdb}
}

func (s *TaskService) CreateGenerateJob(ctx context.Context, input CreateGenerateJobInput) (Job, error) {
	payload, err := json.Marshal(input)
	if err != nil {
		return Job{}, err
	}

	job, err := s.repo.Create(ctx, Job{
		JobType:     "generate",
		Status:      "queued",
		PayloadJSON: string(payload),
	})
	if err != nil {
		return Job{}, err
	}

	if err := s.rdb.XAdd(ctx, &redis.XAddArgs{
		Stream: "stream:generate:jobs",
		Values: map[string]any{
			"job_id":  job.ID,
			"payload": string(payload),
		},
	}).Err(); err != nil {
		return Job{}, err
	}

	return job, nil
}
