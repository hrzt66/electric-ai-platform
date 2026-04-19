package service

import (
	"context"
	"os"
	"path/filepath"
	"testing"
)

type stubRepo struct {
	items []RegistryModel
}

func (s *stubRepo) ListCatalog(ctx context.Context) ([]RegistryModel, error) {
	return s.items, nil
}

func (s *stubRepo) GetByName(ctx context.Context, modelName string) (RegistryModel, error) {
	for _, item := range s.items {
		if item.ModelName == modelName {
			return item, nil
		}
	}
	return RegistryModel{}, nil
}

func TestListModelsReturnsCatalogRecords(t *testing.T) {
	repo := &stubRepo{
		items: []RegistryModel{
			{
				ID:                    1,
				ModelName:             "sd15-electric",
				DisplayName:           "Stable Diffusion 1.5 Electric",
				ModelType:             "generation",
				Status:                "available",
				DefaultPositivePrompt: "500kV substation, industrial realism",
			},
		},
	}

	svc := NewModelService(repo)
	items, err := svc.ListModels(context.Background())
	if err != nil {
		t.Fatalf("expected nil error, got %v", err)
	}
	if len(items) != 1 || items[0].ModelName != "sd15-electric" {
		t.Fatalf("unexpected models: %+v", items)
	}
	if items[0].DefaultPositivePrompt == "" {
		t.Fatalf("expected default prompt to be present: %+v", items[0])
	}
}

func TestGetModelReturnsNamedRecord(t *testing.T) {
	repo := &stubRepo{
		items: []RegistryModel{
			{
				ID:                    2,
				ModelName:             "unipic2-kontext",
				DisplayName:           "UniPic2 Kontext",
				ModelType:             "generation",
				Status:                "experimental",
				DefaultPositivePrompt: "electric inspection robot, substation context",
			},
		},
	}

	svc := NewModelService(repo)
	item, err := svc.GetModel(context.Background(), "unipic2-kontext")
	if err != nil {
		t.Fatalf("expected nil error, got %v", err)
	}
	if item.Status != "experimental" {
		t.Fatalf("expected experimental status, got %+v", item)
	}
}

func TestHydrateStatusMarksLegacyElectricScoreAvailableWhenDependenciesExist(t *testing.T) {
	root := t.TempDir()
	imageRewardDir := filepath.Join(root, "image-reward")
	aestheticDir := filepath.Join(root, "aesthetic-predictor")

	if err := os.MkdirAll(imageRewardDir, 0o755); err != nil {
		t.Fatalf("mkdir image-reward: %v", err)
	}
	if err := os.MkdirAll(aestheticDir, 0o755); err != nil {
		t.Fatalf("mkdir aesthetic-predictor: %v", err)
	}
	if err := os.WriteFile(filepath.Join(imageRewardDir, "config.json"), []byte("{}"), 0o644); err != nil {
		t.Fatalf("write image-reward marker: %v", err)
	}
	if err := os.WriteFile(filepath.Join(aestheticDir, "sac+logos+ava1-l14-linearMSE.pth"), []byte("stub"), 0o644); err != nil {
		t.Fatalf("write aesthetic marker: %v", err)
	}

	item := hydrateStatus(RegistryModel{
		ModelName: "electric-score-v1",
		Status:    "available",
		LocalPath: filepath.Join(root, "electric-score-v1"),
	})

	if item.Status != "available" {
		t.Fatalf("expected legacy electric-score-v1 to be available, got %+v", item)
	}
}

func TestHydrateStatusMarksLegacyElectricScoreUnavailableWhenDependenciesMissing(t *testing.T) {
	root := t.TempDir()
	imageRewardDir := filepath.Join(root, "image-reward")
	if err := os.MkdirAll(imageRewardDir, 0o755); err != nil {
		t.Fatalf("mkdir image-reward: %v", err)
	}
	if err := os.WriteFile(filepath.Join(imageRewardDir, "config.json"), []byte("{}"), 0o644); err != nil {
		t.Fatalf("write image-reward marker: %v", err)
	}

	item := hydrateStatus(RegistryModel{
		ModelName: "electric-score-v1",
		Status:    "available",
		LocalPath: filepath.Join(root, "electric-score-v1"),
	})

	if item.Status != "unavailable" {
		t.Fatalf("expected legacy electric-score-v1 to become unavailable, got %+v", item)
	}
}
