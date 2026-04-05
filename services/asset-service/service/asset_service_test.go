package service

import (
	"context"
	"testing"
)

type memoryAssetRepo struct {
	images []Image
}

func (m *memoryAssetRepo) SaveResult(ctx context.Context, image Image, prompt Prompt, score Score) (Image, error) {
	image.ID = int64(len(m.images) + 1)
	m.images = append(m.images, image)
	return image, nil
}

func TestSaveGenerateResultReturnsPersistedImage(t *testing.T) {
	repo := &memoryAssetRepo{}
	svc := NewAssetService(repo)

	image, err := svc.SaveGenerateResult(context.Background(), SaveGenerateResultInput{
		JobID:                1,
		ImageName:            "job-1.png",
		FilePath:             "storage/images/job-1.png",
		ModelName:            "UniPic-2",
		PositivePrompt:       "A wind turbine farm at sunset",
		NegativePrompt:       "blurry",
		SamplingSteps:        20,
		Seed:                 42,
		GuidanceScale:        7.5,
		VisualFidelity:       75,
		TextConsistency:      78,
		PhysicalPlausibility: 76,
		CompositionAesthetics: 73,
		TotalScore:           75.7,
	})
	if err != nil {
		t.Fatalf("expected nil error, got %v", err)
	}
	if image.ID == 0 {
		t.Fatal("expected generated image id")
	}
}
