package service

import (
	"context"
	"testing"
)

type memoryAssetRepo struct {
	nextID  int64
	records []HistoryItem
}

func (m *memoryAssetRepo) SaveResults(ctx context.Context, jobID int64, items []PersistAssetResult) ([]HistoryItem, error) {
	saved := make([]HistoryItem, 0, len(items))
	for _, item := range items {
		m.nextID++
		record := HistoryItem{
			ID:                    m.nextID,
			JobID:                 jobID,
			ImageName:             item.ImageName,
			FilePath:              item.FilePath,
			ModelName:             item.ModelName,
			Status:                "scored",
			PositivePrompt:        item.PositivePrompt,
			NegativePrompt:        item.NegativePrompt,
			SamplingSteps:         item.SamplingSteps,
			Seed:                  item.Seed,
			GuidanceScale:         item.GuidanceScale,
			VisualFidelity:        item.VisualFidelity,
			TextConsistency:       item.TextConsistency,
			PhysicalPlausibility:  item.PhysicalPlausibility,
			CompositionAesthetics: item.CompositionAesthetics,
			TotalScore:            item.TotalScore,
		}
		m.records = append(m.records, record)
		saved = append(saved, record)
	}
	return saved, nil
}

func (m *memoryAssetRepo) ListHistory(ctx context.Context) ([]HistoryItem, error) {
	return m.records, nil
}

func (m *memoryAssetRepo) GetDetail(ctx context.Context, id int64) (AssetDetail, error) {
	for _, record := range m.records {
		if record.ID == id {
			return AssetDetail{
				Asset: Image{
					ID:        record.ID,
					JobID:     record.JobID,
					ImageName: record.ImageName,
					FilePath:  record.FilePath,
					ModelName: record.ModelName,
					Status:    record.Status,
				},
				Prompt: Prompt{
					PositivePrompt: record.PositivePrompt,
					NegativePrompt: record.NegativePrompt,
					SamplingSteps:  record.SamplingSteps,
					Seed:           record.Seed,
					GuidanceScale:  record.GuidanceScale,
				},
				Score: Score{
					VisualFidelity:        record.VisualFidelity,
					TextConsistency:       record.TextConsistency,
					PhysicalPlausibility:  record.PhysicalPlausibility,
					CompositionAesthetics: record.CompositionAesthetics,
					TotalScore:            record.TotalScore,
				},
			}, nil
		}
	}
	return AssetDetail{}, nil
}

func TestSaveGenerateResultsReturnsPersistedImages(t *testing.T) {
	repo := &memoryAssetRepo{}
	svc := NewAssetService(repo)

	items, err := svc.SaveGenerateResults(context.Background(), SaveGenerateResultsInput{
		JobID: 1,
		Results: []SaveGenerateAssetInput{{
			ImageName:             "job-1.png",
			FilePath:              "storage/images/job-1.png",
			ModelName:             "sd15-electric",
			PositivePrompt:        "A wind turbine farm at sunset",
			NegativePrompt:        "blurry",
			SamplingSteps:         20,
			Seed:                  42,
			GuidanceScale:         7.5,
			VisualFidelity:        75,
			TextConsistency:       78,
			PhysicalPlausibility:  76,
			CompositionAesthetics: 73,
			TotalScore:            75.7,
		}},
	})
	if err != nil {
		t.Fatalf("expected nil error, got %v", err)
	}
	if len(items) != 1 {
		t.Fatalf("expected 1 persisted image, got %d", len(items))
	}
	if items[0].ID == 0 {
		t.Fatal("expected generated image id")
	}
}

func TestListHistoryReturnsSavedItems(t *testing.T) {
	repo := &memoryAssetRepo{}
	svc := NewAssetService(repo)

	_, err := svc.SaveGenerateResults(context.Background(), SaveGenerateResultsInput{
		JobID: 5,
		Results: []SaveGenerateAssetInput{{
			ImageName:             "job-5.png",
			FilePath:              "storage/images/job-5.png",
			ModelName:             "sd15-electric",
			PositivePrompt:        "substation",
			NegativePrompt:        "blurry",
			SamplingSteps:         30,
			Seed:                  100,
			GuidanceScale:         7.5,
			VisualFidelity:        88,
			TextConsistency:       89,
			PhysicalPlausibility:  90,
			CompositionAesthetics: 80,
			TotalScore:            87.2,
		}},
	})
	if err != nil {
		t.Fatalf("expected nil error, got %v", err)
	}

	items, err := svc.ListHistory(context.Background())
	if err != nil {
		t.Fatalf("expected nil error, got %v", err)
	}
	if len(items) != 1 {
		t.Fatalf("expected 1 history item, got %d", len(items))
	}
	if items[0].ModelName != "sd15-electric" {
		t.Fatalf("expected sd15-electric model, got %s", items[0].ModelName)
	}
}

func TestListHistoryReturnsEmptySliceWhenRepositoryHasNoRows(t *testing.T) {
	repo := &memoryAssetRepo{}
	svc := NewAssetService(repo)

	items, err := svc.ListHistory(context.Background())
	if err != nil {
		t.Fatalf("expected nil error, got %v", err)
	}
	if items == nil {
		t.Fatal("expected empty slice, got nil")
	}
	if len(items) != 0 {
		t.Fatalf("expected 0 history items, got %d", len(items))
	}
}

func TestGetAssetDetailReturnsPromptAndScore(t *testing.T) {
	repo := &memoryAssetRepo{}
	svc := NewAssetService(repo)

	items, err := svc.SaveGenerateResults(context.Background(), SaveGenerateResultsInput{
		JobID: 9,
		Results: []SaveGenerateAssetInput{{
			ImageName:             "job-9.png",
			FilePath:              "storage/images/job-9.png",
			ModelName:             "sd15-electric",
			PositivePrompt:        "inspection robot in substation",
			NegativePrompt:        "artifact",
			SamplingSteps:         28,
			Seed:                  456,
			GuidanceScale:         7,
			VisualFidelity:        82,
			TextConsistency:       84,
			PhysicalPlausibility:  81,
			CompositionAesthetics: 79,
			TotalScore:            81.8,
		}},
	})
	if err != nil {
		t.Fatalf("expected nil error, got %v", err)
	}

	detail, err := svc.GetAssetDetail(context.Background(), items[0].ID)
	if err != nil {
		t.Fatalf("expected nil error, got %v", err)
	}
	if detail.Prompt.PositivePrompt != "inspection robot in substation" {
		t.Fatalf("expected positive prompt to persist, got %s", detail.Prompt.PositivePrompt)
	}
	if detail.Score.TotalScore != 81.8 {
		t.Fatalf("expected total score 81.8, got %f", detail.Score.TotalScore)
	}
}
