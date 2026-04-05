package service

import (
	"context"

	"electric-ai/services/asset-service/model"
)

type Image = model.Image
type Prompt = model.Prompt
type Score = model.Score
type SaveGenerateResultInput = model.SaveGenerateResultInput

type Repository interface {
	SaveResult(ctx context.Context, image Image, prompt Prompt, score Score) (Image, error)
}

type AssetService struct {
	repo Repository
}

func NewAssetService(repo Repository) *AssetService {
	return &AssetService{repo: repo}
}

func (s *AssetService) SaveGenerateResult(ctx context.Context, input SaveGenerateResultInput) (Image, error) {
	return s.repo.SaveResult(
		ctx,
		Image{
			JobID:     input.JobID,
			ImageName: input.ImageName,
			FilePath:  input.FilePath,
			ModelName: input.ModelName,
			Status:    "scored",
		},
		Prompt{
			PositivePrompt: input.PositivePrompt,
			NegativePrompt: input.NegativePrompt,
			SamplingSteps:  input.SamplingSteps,
			Seed:           input.Seed,
			GuidanceScale:  input.GuidanceScale,
		},
		Score{
			VisualFidelity:        input.VisualFidelity,
			TextConsistency:       input.TextConsistency,
			PhysicalPlausibility:  input.PhysicalPlausibility,
			CompositionAesthetics: input.CompositionAesthetics,
			TotalScore:            input.TotalScore,
		},
	)
}
