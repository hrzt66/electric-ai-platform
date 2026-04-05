package repository

import (
	"context"
	"database/sql"

	"electric-ai/services/asset-service/model"
)

type AssetRepository struct {
	db *sql.DB
}

func NewAssetRepository(db *sql.DB) *AssetRepository {
	return &AssetRepository{db: db}
}

func (r *AssetRepository) SaveResult(ctx context.Context, image model.Image, prompt model.Prompt, score model.Score) (model.Image, error) {
	tx, err := r.db.BeginTx(ctx, nil)
	if err != nil {
		return model.Image{}, err
	}

	committed := false
	defer func() {
		if !committed {
			_ = tx.Rollback()
		}
	}()

	imageResult, err := tx.ExecContext(ctx, `
INSERT INTO asset_images (job_id, image_name, file_path, model_name, status)
VALUES (?, ?, ?, ?, ?)
`, image.JobID, image.ImageName, image.FilePath, image.ModelName, image.Status)
	if err != nil {
		return model.Image{}, err
	}

	imageID, err := imageResult.LastInsertId()
	if err != nil {
		return model.Image{}, err
	}

	if _, err := tx.ExecContext(ctx, `
INSERT INTO asset_image_prompts (image_id, positive_prompt, negative_prompt, sampling_steps, seed, guidance_scale)
VALUES (?, ?, ?, ?, ?, ?)
`, imageID, prompt.PositivePrompt, prompt.NegativePrompt, prompt.SamplingSteps, prompt.Seed, prompt.GuidanceScale); err != nil {
		return model.Image{}, err
	}

	if _, err := tx.ExecContext(ctx, `
INSERT INTO asset_image_scores (image_id, visual_fidelity, text_consistency, physical_plausibility, composition_aesthetics, total_score)
VALUES (?, ?, ?, ?, ?, ?)
`, imageID, score.VisualFidelity, score.TextConsistency, score.PhysicalPlausibility, score.CompositionAesthetics, score.TotalScore); err != nil {
		return model.Image{}, err
	}

	if err := tx.Commit(); err != nil {
		return model.Image{}, err
	}

	committed = true
	image.ID = imageID
	return image, nil
}
