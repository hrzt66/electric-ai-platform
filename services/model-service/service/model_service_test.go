package service

import (
	"context"
	"testing"
)

type stubRepo struct {
	items []RegistryModel
}

func (s *stubRepo) ListActive(ctx context.Context) ([]RegistryModel, error) {
	return s.items, nil
}

func TestListActiveModelsReturnsOnlyActiveRecords(t *testing.T) {
	repo := &stubRepo{
		items: []RegistryModel{
			{ID: 1, ModelName: "UniPic-2", ModelType: "generation", Status: "active"},
		},
	}

	svc := NewModelService(repo)
	items, err := svc.ListActive(context.Background())
	if err != nil {
		t.Fatalf("expected nil error, got %v", err)
	}
	if len(items) != 1 || items[0].ModelName != "UniPic-2" {
		t.Fatalf("unexpected models: %+v", items)
	}
}
