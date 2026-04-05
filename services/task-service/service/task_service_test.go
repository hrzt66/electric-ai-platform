package service

import (
	"context"
	"testing"
	"time"

	"github.com/alicebob/miniredis/v2"
	"github.com/redis/go-redis/v9"
)

type memoryRepo struct {
	nextID int64
	items  map[int64]Job
}

func (m *memoryRepo) Create(ctx context.Context, job Job) (Job, error) {
	if m.items == nil {
		m.items = map[int64]Job{}
	}
	m.nextID++
	job.ID = m.nextID
	job.CreatedAt = time.Unix(1700000000, 0).UTC()
	job.UpdatedAt = job.CreatedAt
	m.items[job.ID] = job
	return job, nil
}

func (m *memoryRepo) GetByID(ctx context.Context, id int64) (Job, error) {
	return m.items[id], nil
}

func (m *memoryRepo) List(ctx context.Context) ([]Job, error) {
	items := make([]Job, 0, len(m.items))
	for _, item := range m.items {
		items = append(items, item)
	}
	return items, nil
}

func (m *memoryRepo) UpdateStatus(ctx context.Context, id int64, input UpdateJobStatusInput) (Job, error) {
	job := m.items[id]
	job.Status = input.Status
	job.Stage = input.Stage
	job.ErrorMessage = input.ErrorMessage
	job.UpdatedAt = time.Unix(1700000100, 0).UTC()
	m.items[id] = job
	return job, nil
}

func TestCreateGenerateJobStoresJobAndPublishesToRedis(t *testing.T) {
	mr := miniredis.RunT(t)
	rdb := redis.NewClient(&redis.Options{Addr: mr.Addr()})
	repo := &memoryRepo{}
	svc := NewTaskService(repo, rdb)

	job, err := svc.CreateGenerateJob(context.Background(), CreateGenerateJobInput{
		Prompt:         "A wind turbine farm at sunset",
		NegativePrompt: "blurry",
		ModelName:      "UniPic-2",
	})
	if err != nil {
		t.Fatalf("expected nil error, got %v", err)
	}
	if job.Status != "queued" {
		t.Fatalf("expected queued status, got %s", job.Status)
	}
	if mr.Exists("stream:generate:jobs") == false {
		t.Fatal("expected stream entry")
	}
}

func TestGetJobReturnsStoredRecord(t *testing.T) {
	mr := miniredis.RunT(t)
	rdb := redis.NewClient(&redis.Options{Addr: mr.Addr()})
	repo := &memoryRepo{}
	svc := NewTaskService(repo, rdb)

	created, err := svc.CreateGenerateJob(context.Background(), CreateGenerateJobInput{
		Prompt:         "500kV substation",
		NegativePrompt: "blurry",
		ModelName:      "sd15-electric",
	})
	if err != nil {
		t.Fatalf("expected nil error, got %v", err)
	}

	job, err := svc.GetJob(context.Background(), created.ID)
	if err != nil {
		t.Fatalf("expected nil error, got %v", err)
	}
	if job.ModelName != "sd15-electric" {
		t.Fatalf("expected model name to be persisted, got %s", job.ModelName)
	}
	if job.Stage != "queued" {
		t.Fatalf("expected stage queued, got %s", job.Stage)
	}
}

func TestUpdateStatusWritesStageAndErrorMessage(t *testing.T) {
	mr := miniredis.RunT(t)
	rdb := redis.NewClient(&redis.Options{Addr: mr.Addr()})
	repo := &memoryRepo{}
	svc := NewTaskService(repo, rdb)

	created, err := svc.CreateGenerateJob(context.Background(), CreateGenerateJobInput{
		Prompt:         "inspection drone over power line",
		NegativePrompt: "artifact",
		ModelName:      "sd15-electric",
	})
	if err != nil {
		t.Fatalf("expected nil error, got %v", err)
	}

	job, err := svc.UpdateStatus(context.Background(), created.ID, UpdateJobStatusInput{
		Status:       "failed",
		Stage:        "failed",
		ErrorMessage: "generation crashed",
	})
	if err != nil {
		t.Fatalf("expected nil error, got %v", err)
	}
	if job.Status != "failed" {
		t.Fatalf("expected failed status, got %s", job.Status)
	}
	if job.ErrorMessage != "generation crashed" {
		t.Fatalf("expected error message to persist, got %s", job.ErrorMessage)
	}
}
