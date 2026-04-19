package service

import (
	"context"
	"encoding/json"
	"math"
	"strings"
	"testing"
)

type memoryAssetRepo struct {
	nextID           int64
	records          []HistoryItem
	checkedImagePath map[int64]string
	explanations     map[int64]json.RawMessage
}

func (m *memoryAssetRepo) SaveResults(ctx context.Context, jobID int64, items []PersistAssetResult) ([]HistoryItem, error) {
	if m.checkedImagePath == nil {
		m.checkedImagePath = make(map[int64]string)
	}
	if m.explanations == nil {
		m.explanations = make(map[int64]json.RawMessage)
	}
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
		m.checkedImagePath[m.nextID] = item.CheckedImagePath
		if len(item.ScoreExplanation) > 0 {
			m.explanations[m.nextID] = append(json.RawMessage(nil), item.ScoreExplanation...)
		}
		saved = append(saved, record)
	}
	return saved, nil
}

func (m *memoryAssetRepo) ListHistory(ctx context.Context) ([]HistoryItem, error) {
	return m.records, nil
}

func (m *memoryAssetRepo) ListHistoryPage(ctx context.Context, query HistoryPageQuery) (HistoryPageResult, error) {
	filtered := make([]HistoryItem, 0, len(m.records))
	for _, item := range m.records {
		if query.ModelName != "" && !strings.Contains(strings.ToLower(item.ModelName), strings.ToLower(query.ModelName)) {
			continue
		}
		if query.Status != "" && query.Status != "all" && item.Status != query.Status {
			continue
		}
		if query.PromptKeyword != "" {
			keyword := strings.ToLower(query.PromptKeyword)
			if !strings.Contains(strings.ToLower(item.PositivePrompt), keyword) && !strings.Contains(strings.ToLower(item.ImageName), keyword) {
				continue
			}
		}
		if item.TotalScore < query.MinTotalScore {
			continue
		}
		filtered = append(filtered, item)
	}

	total := len(filtered)
	start := (query.Page - 1) * query.PageSize
	if start >= total {
		return HistoryPageResult{
			Items:      []HistoryItem{},
			Page:       query.Page,
			PageSize:   query.PageSize,
			Total:      total,
			TotalPages: int(math.Ceil(float64(total) / float64(query.PageSize))),
		}, nil
	}
	end := start + query.PageSize
	if end > total {
		end = total
	}
	return HistoryPageResult{
		Items:      append([]HistoryItem(nil), filtered[start:end]...),
		Page:       query.Page,
		PageSize:   query.PageSize,
		Total:      total,
		TotalPages: int(math.Ceil(float64(total) / float64(query.PageSize))),
	}, nil
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
				CheckedImagePath: m.checkedImagePath[record.ID],
				ScoreExplanation: m.explanations[record.ID],
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

func TestSaveGenerateResultsSkipsAlreadyPersistedImageForSameJob(t *testing.T) {
	repo := &memoryAssetRepo{}
	svc := NewAssetService(repo)

	input := SaveGenerateResultsInput{
		JobID: 21,
		Results: []SaveGenerateAssetInput{{
			ImageName:             "21_0_123.png",
			FilePath:              "storage/images/21_0_123.png",
			ModelName:             "sd15-electric",
			PositivePrompt:        "substation",
			NegativePrompt:        "blurry",
			SamplingSteps:         20,
			Seed:                  123,
			GuidanceScale:         7.5,
			VisualFidelity:        80,
			TextConsistency:       82,
			PhysicalPlausibility:  81,
			CompositionAesthetics: 79,
			TotalScore:            80.5,
		}},
	}

	firstSaved, err := svc.SaveGenerateResults(context.Background(), input)
	if err != nil {
		t.Fatalf("expected nil error on first save, got %v", err)
	}
	if len(firstSaved) != 1 {
		t.Fatalf("expected 1 saved item on first save, got %d", len(firstSaved))
	}

	secondSaved, err := svc.SaveGenerateResults(context.Background(), input)
	if err != nil {
		t.Fatalf("expected nil error on duplicate save, got %v", err)
	}
	if len(secondSaved) != 1 {
		t.Fatalf("expected duplicate save to return the existing item, got %d", len(secondSaved))
	}

	history, err := svc.ListHistory(context.Background())
	if err != nil {
		t.Fatalf("expected nil error when listing history, got %v", err)
	}
	if len(history) != 1 {
		t.Fatalf("expected 1 history item after duplicate save, got %d", len(history))
	}
}

func TestGetAssetDetailReturnsSavedScoreExplanation(t *testing.T) {
	repo := &memoryAssetRepo{}
	svc := NewAssetService(repo)

	items, err := svc.SaveGenerateResults(context.Background(), SaveGenerateResultsInput{
		JobID: 30,
		Results: []SaveGenerateAssetInput{{
			ImageName:             "30_0_100.png",
			FilePath:              "storage/images/30_0_100.png",
			ModelName:             "ssd1b-electric",
			PositivePrompt:        "night maintenance on transmission tower",
			NegativePrompt:        "artifact",
			SamplingSteps:         20,
			Seed:                  100,
			GuidanceScale:         7.5,
			VisualFidelity:        60.87,
			TextConsistency:       42.66,
			PhysicalPlausibility:  42.39,
			CompositionAesthetics: 65.93,
			TotalScore:            50.61,
			CheckedImagePath:      "model/image_check/30_0_100.png",
			ScoreExplanation: json.RawMessage(`{
				"checked_image_path":"model/image_check/30_0_100.png",
				"dimensions":{
					"text_consistency":{
						"uses_yolo":true,
						"summary":"检测到 tower，但 line 和 insulator 缺失。"
					}
				}
			}`),
		}},
	})
	if err != nil {
		t.Fatalf("expected nil error, got %v", err)
	}

	detail, err := svc.GetAssetDetail(context.Background(), items[0].ID)
	if err != nil {
		t.Fatalf("expected nil error, got %v", err)
	}
	if detail.CheckedImagePath != "model/image_check/30_0_100.png" {
		t.Fatalf("expected checked image path to persist, got %s", detail.CheckedImagePath)
	}
	if len(detail.ScoreExplanation) == 0 {
		t.Fatal("expected score explanation to persist")
	}
}

func TestListHistoryPageReturnsPagedSliceAndTotals(t *testing.T) {
	repo := &memoryAssetRepo{
		records: []HistoryItem{
			{
				ID:             3,
				JobID:          9,
				ImageName:      "3.png",
				FilePath:       "model/image/3.png",
				ModelName:      "ssd1b-electric",
				Status:         "scored",
				PositivePrompt: "night substation tower",
				TotalScore:     78.6,
			},
			{
				ID:             2,
				JobID:          8,
				ImageName:      "2.png",
				FilePath:       "model/image/2.png",
				ModelName:      "ssd1b-electric",
				Status:         "scored",
				PositivePrompt: "substation yard overview",
				TotalScore:     65.2,
			},
			{
				ID:             1,
				JobID:          7,
				ImageName:      "1.png",
				FilePath:       "model/image/1.png",
				ModelName:      "sd15-electric",
				Status:         "generated",
				PositivePrompt: "hydro dam",
				TotalScore:     41.3,
			},
		},
	}
	svc := NewAssetService(repo)

	page, err := svc.ListHistoryPage(context.Background(), HistoryPageQuery{
		Page:      2,
		PageSize:  1,
		ModelName: "ssd1b-electric",
	})
	if err != nil {
		t.Fatalf("expected nil error, got %v", err)
	}
	if page.Total != 2 {
		t.Fatalf("expected total 2, got %d", page.Total)
	}
	if page.TotalPages != 2 {
		t.Fatalf("expected total pages 2, got %d", page.TotalPages)
	}
	if page.Page != 2 || page.PageSize != 1 {
		t.Fatalf("unexpected page metadata: %+v", page)
	}
	if len(page.Items) != 1 {
		t.Fatalf("expected 1 paged item, got %d", len(page.Items))
	}
	if page.Items[0].ID != 2 {
		t.Fatalf("expected second ssd1b item on page 2, got %+v", page.Items[0])
	}
}
