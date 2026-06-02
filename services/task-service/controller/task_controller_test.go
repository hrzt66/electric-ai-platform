package controller_test

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/alicebob/miniredis/v2"
	"github.com/redis/go-redis/v9"

	taskcontroller "electric-ai/services/task-service/controller"
	"electric-ai/services/task-service/model"
	taskrouter "electric-ai/services/task-service/router"
	"electric-ai/services/task-service/service"
)

type stubTaskRepo struct {
	pageResult model.JobPageResult
}

func (s *stubTaskRepo) Create(ctx context.Context, job service.Job) (service.Job, error) {
	return service.Job{}, nil
}

func (s *stubTaskRepo) GetByID(ctx context.Context, id int64) (service.Job, error) {
	return service.Job{}, nil
}

func (s *stubTaskRepo) List(ctx context.Context) ([]service.Job, error) {
	return []service.Job{}, nil
}

func (s *stubTaskRepo) ListPage(ctx context.Context, query service.JobPageQuery) (service.JobPageResult, error) {
	return service.JobPageResult(s.pageResult), nil
}

func (s *stubTaskRepo) UpdateStatus(ctx context.Context, id int64, input service.UpdateJobStatusInput) (service.Job, error) {
	return service.Job{}, nil
}

func TestListJobsPageReturnsPagedEnvelope(t *testing.T) {
	mr := miniredis.RunT(t)
	rdb := redis.NewClient(&redis.Options{Addr: mr.Addr()})
	repo := &stubTaskRepo{
		pageResult: model.JobPageResult{
			Items: []model.Job{
				{ID: 124, JobType: "generate", Status: "completed", Stage: "completed", ModelName: "sd15-electric"},
			},
			Page:       2,
			PageSize:   10,
			Total:      124,
			TotalPages: 13,
		},
	}

	engine := taskrouter.New(taskcontroller.NewTaskController(service.NewTaskService(repo, rdb)))
	req := httptest.NewRequest(http.MethodGet, "/api/v1/tasks/page?page=2&page_size=10", nil)
	rec := httptest.NewRecorder()
	engine.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d with body %s", rec.Code, rec.Body.String())
	}

	var response struct {
		Code int `json:"code"`
		Data struct {
			Items      []model.Job `json:"items"`
			Page       int         `json:"page"`
			PageSize   int         `json:"page_size"`
			Total      int         `json:"total"`
			TotalPages int         `json:"total_pages"`
		} `json:"data"`
	}
	if err := json.Unmarshal(rec.Body.Bytes(), &response); err != nil {
		t.Fatalf("unmarshal response: %v", err)
	}

	if response.Data.Page != 2 || response.Data.PageSize != 10 || response.Data.Total != 124 || response.Data.TotalPages != 13 {
		t.Fatalf("unexpected pagination payload: %+v", response.Data)
	}
	if len(response.Data.Items) != 1 || response.Data.Items[0].ID != 124 {
		t.Fatalf("unexpected items payload: %+v", response.Data.Items)
	}
}
