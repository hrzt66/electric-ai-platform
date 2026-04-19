package controller_test

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"

	assetcontroller "electric-ai/services/asset-service/controller"
	"electric-ai/services/asset-service/model"
	assetrouter "electric-ai/services/asset-service/router"
	"electric-ai/services/asset-service/service"
)

type stubRepo struct {
	paged model.HistoryPageResult
	query model.HistoryPageQuery
}

func (s *stubRepo) SaveResults(ctx context.Context, jobID int64, items []service.PersistAssetResult) ([]service.HistoryItem, error) {
	return nil, nil
}

func (s *stubRepo) ListHistory(ctx context.Context) ([]service.HistoryItem, error) {
	return []service.HistoryItem{}, nil
}

func (s *stubRepo) ListHistoryPage(ctx context.Context, query service.HistoryPageQuery) (service.HistoryPageResult, error) {
	s.query = model.HistoryPageQuery(query)
	return service.HistoryPageResult(s.paged), nil
}

func (s *stubRepo) GetDetail(ctx context.Context, id int64) (service.AssetDetail, error) {
	return service.AssetDetail{}, nil
}

func TestListHistoryPageReturnsPagedEnvelope(t *testing.T) {
	gin.SetMode(gin.TestMode)

	repo := &stubRepo{
		paged: model.HistoryPageResult{
			Items: []model.HistoryItem{
				{ID: 5, ImageName: "5.png", ModelName: "ssd1b-electric", TotalScore: 74.2},
			},
			Page:       2,
			PageSize:   20,
			Total:      41,
			TotalPages: 3,
		},
	}
	engine := assetrouter.New(assetcontroller.NewAssetController(service.NewAssetService(repo)))

	req := httptest.NewRequest(http.MethodGet, "/api/v1/assets/history/page?page=2&page_size=20&model_name=ssd1b-electric", nil)
	rec := httptest.NewRecorder()
	engine.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d with body %s", rec.Code, rec.Body.String())
	}

	var response struct {
		Code int `json:"code"`
		Data struct {
			Items      []model.HistoryItem `json:"items"`
			Page       int                 `json:"page"`
			PageSize   int                 `json:"page_size"`
			Total      int                 `json:"total"`
			TotalPages int                 `json:"total_pages"`
		} `json:"data"`
	}
	if err := json.Unmarshal(rec.Body.Bytes(), &response); err != nil {
		t.Fatalf("unmarshal response: %v", err)
	}

	if response.Data.Page != 2 || response.Data.PageSize != 20 {
		t.Fatalf("unexpected pagination payload: %+v", response.Data)
	}
	if len(response.Data.Items) != 1 || response.Data.Items[0].ID != 5 {
		t.Fatalf("unexpected items payload: %+v", response.Data.Items)
	}
	if repo.query.ModelName != "ssd1b-electric" {
		t.Fatalf("expected controller to forward query filters, got %+v", repo.query)
	}
}
