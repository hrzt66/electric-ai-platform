package service

import (
	"context"
	"testing"

	"github.com/alicebob/miniredis/v2"
	"github.com/redis/go-redis/v9"
)

type memoryRepo struct {
	nextID int64
	items  []Job
}

func (m *memoryRepo) Create(ctx context.Context, job Job) (Job, error) {
	m.nextID++
	job.ID = m.nextID
	m.items = append(m.items, job)
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
