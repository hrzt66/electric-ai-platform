package service

import (
	"context"
	"encoding/json"

	"github.com/redis/go-redis/v9"

	"electric-ai/services/task-service/model"
)

type Job = model.Job
type CreateGenerateJobInput = model.CreateGenerateJobInput
type UpdateJobStatusInput = model.UpdateJobStatusInput

type Repository interface {
	Create(ctx context.Context, job Job) (Job, error)
	GetByID(ctx context.Context, id int64) (Job, error)
	List(ctx context.Context) ([]Job, error)
	UpdateStatus(ctx context.Context, id int64, input UpdateJobStatusInput) (Job, error)
}

type TaskService struct {
	repo Repository
	rdb  *redis.Client
}

func NewTaskService(repo Repository, rdb *redis.Client) *TaskService {
	return &TaskService{repo: repo, rdb: rdb}
}

func (s *TaskService) CreateGenerateJob(ctx context.Context, input CreateGenerateJobInput) (Job, error) {
	if input.ScoringModelName == "" {
		input.ScoringModelName = "electric-score-v1"
	}

	payload, err := json.Marshal(input)
	if err != nil {
		return Job{}, err
	}

	job, err := s.repo.Create(ctx, Job{
		JobType:          "generate",
		Status:           "queued",
		Stage:            "queued",
		ModelName:        input.ModelName,
		ScoringModelName: input.ScoringModelName,
		Prompt:           input.Prompt,
		NegativePrompt:   input.NegativePrompt,
		PayloadJSON:      string(payload),
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

func (s *TaskService) GetJob(ctx context.Context, id int64) (Job, error) {
	return s.repo.GetByID(ctx, id)
}

func (s *TaskService) ListJobs(ctx context.Context) ([]Job, error) {
	return s.repo.List(ctx)
}

func (s *TaskService) UpdateStatus(ctx context.Context, id int64, input UpdateJobStatusInput) (Job, error) {
	return s.repo.UpdateStatus(ctx, id, input)
}
