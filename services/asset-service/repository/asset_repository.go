package repository

import (
	"context"
	"database/sql"
	"strings"
	"sync"

	"electric-ai/services/asset-service/model"
)

// AssetRepository 封装资产、提示词和评分三张表的读写逻辑。
type AssetRepository struct {
	db         *sql.DB
	schemaOnce sync.Once
	schemaErr  error
}

// NewAssetRepository 创建资产仓储实例。
func NewAssetRepository(db *sql.DB) *AssetRepository {
	return &AssetRepository{db: db}
}

// ensureSchema 在首次使用时补齐资产相关表结构。
func (r *AssetRepository) ensureSchema(ctx context.Context) error {
	r.schemaOnce.Do(func() {
		const imageTable = `
CREATE TABLE IF NOT EXISTS asset_images (
	id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
	job_id BIGINT NOT NULL,
	image_name VARCHAR(255) NOT NULL,
	file_path TEXT NOT NULL,
	model_name VARCHAR(128) NOT NULL,
	status VARCHAR(32) NOT NULL,
	created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
	updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
)
`
		const promptTable = `
CREATE TABLE IF NOT EXISTS asset_image_prompts (
	image_id BIGINT NOT NULL PRIMARY KEY,
	positive_prompt TEXT,
	negative_prompt TEXT,
	sampling_steps INT NOT NULL,
	seed BIGINT NOT NULL,
	guidance_scale DOUBLE NOT NULL
)
`
		const scoreTable = `
CREATE TABLE IF NOT EXISTS asset_image_scores (
	image_id BIGINT NOT NULL PRIMARY KEY,
	visual_fidelity DOUBLE NOT NULL,
	text_consistency DOUBLE NOT NULL,
	physical_plausibility DOUBLE NOT NULL,
	composition_aesthetics DOUBLE NOT NULL,
	total_score DOUBLE NOT NULL
)
`
		const explanationTable = `
CREATE TABLE IF NOT EXISTS asset_image_score_explanations (
	image_id BIGINT NOT NULL PRIMARY KEY,
	checked_image_path TEXT NULL,
	explanation_json LONGTEXT NOT NULL,
	created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
)
`
		if _, r.schemaErr = r.db.ExecContext(ctx, imageTable); r.schemaErr != nil {
			return
		}
		if _, r.schemaErr = r.db.ExecContext(ctx, promptTable); r.schemaErr != nil {
			return
		}
		if _, r.schemaErr = r.db.ExecContext(ctx, scoreTable); r.schemaErr != nil {
			return
		}
		if _, r.schemaErr = r.db.ExecContext(ctx, explanationTable); r.schemaErr != nil {
			return
		}
	})
	return r.schemaErr
}

// SaveResults 把一批生成结果写入资产、提示词和评分表，并返回写入后的历史记录。
func (r *AssetRepository) SaveResults(ctx context.Context, jobID int64, items []model.PersistAssetResult) ([]model.HistoryItem, error) {
	if err := r.ensureSchema(ctx); err != nil {
		return nil, err
	}

	tx, err := r.db.BeginTx(ctx, nil)
	if err != nil {
		return nil, err
	}

	committed := false
	defer func() {
		if !committed {
			_ = tx.Rollback()
		}
	}()

	savedIDs := make([]int64, 0, len(items))
	for _, item := range items {
		imageResult, err := tx.ExecContext(ctx, `
INSERT INTO asset_images (job_id, image_name, file_path, model_name, status)
VALUES (?, ?, ?, ?, ?)
`, jobID, item.ImageName, item.FilePath, item.ModelName, "scored")
		if err != nil {
			return nil, err
		}

		imageID, err := imageResult.LastInsertId()
		if err != nil {
			return nil, err
		}
		savedIDs = append(savedIDs, imageID)

		if _, err := tx.ExecContext(ctx, `
INSERT INTO asset_image_prompts (image_id, positive_prompt, negative_prompt, sampling_steps, seed, guidance_scale)
VALUES (?, ?, ?, ?, ?, ?)
`, imageID, item.PositivePrompt, item.NegativePrompt, item.SamplingSteps, item.Seed, item.GuidanceScale); err != nil {
			return nil, err
		}

		if _, err := tx.ExecContext(ctx, `
INSERT INTO asset_image_scores (image_id, visual_fidelity, text_consistency, physical_plausibility, composition_aesthetics, total_score)
VALUES (?, ?, ?, ?, ?, ?)
`, imageID, item.VisualFidelity, item.TextConsistency, item.PhysicalPlausibility, item.CompositionAesthetics, item.TotalScore); err != nil {
			return nil, err
		}

		if len(item.ScoreExplanation) > 0 || item.CheckedImagePath != "" {
			explanationPayload := string(item.ScoreExplanation)
			if explanationPayload == "" {
				explanationPayload = `{}`
			}
			if _, err := tx.ExecContext(ctx, `
INSERT INTO asset_image_score_explanations (image_id, checked_image_path, explanation_json)
VALUES (?, ?, ?)
`, imageID, item.CheckedImagePath, explanationPayload); err != nil {
				return nil, err
			}
		}
	}

	if err := tx.Commit(); err != nil {
		return nil, err
	}

	committed = true

	results := make([]model.HistoryItem, 0, len(savedIDs))
	for _, id := range savedIDs {
		detail, err := r.GetDetail(ctx, id)
		if err != nil {
			return nil, err
		}
		results = append(results, model.HistoryItem{
			ID:                    detail.Asset.ID,
			JobID:                 detail.Asset.JobID,
			ImageName:             detail.Asset.ImageName,
			FilePath:              detail.Asset.FilePath,
			ModelName:             detail.Asset.ModelName,
			Status:                detail.Asset.Status,
			PositivePrompt:        detail.Prompt.PositivePrompt,
			NegativePrompt:        detail.Prompt.NegativePrompt,
			SamplingSteps:         detail.Prompt.SamplingSteps,
			Seed:                  detail.Prompt.Seed,
			GuidanceScale:         detail.Prompt.GuidanceScale,
			VisualFidelity:        detail.Score.VisualFidelity,
			TextConsistency:       detail.Score.TextConsistency,
			PhysicalPlausibility:  detail.Score.PhysicalPlausibility,
			CompositionAesthetics: detail.Score.CompositionAesthetics,
			TotalScore:            detail.Score.TotalScore,
			CreatedAt:             detail.Asset.CreatedAt,
		})
	}

	return results, nil
}

// ListHistory 联表查询历史中心所需的聚合结果。
func (r *AssetRepository) ListHistory(ctx context.Context) ([]model.HistoryItem, error) {
	if err := r.ensureSchema(ctx); err != nil {
		return nil, err
	}

	rows, err := r.db.QueryContext(ctx, `
SELECT i.id, i.job_id, i.image_name, i.file_path, i.model_name, i.status,
       p.positive_prompt, p.negative_prompt, p.sampling_steps, p.seed, p.guidance_scale,
       s.visual_fidelity, s.text_consistency, s.physical_plausibility, s.composition_aesthetics, s.total_score,
       i.created_at
FROM asset_images i
JOIN asset_image_prompts p ON p.image_id = i.id
JOIN asset_image_scores s ON s.image_id = i.id
ORDER BY i.id DESC
LIMIT 100
`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var items []model.HistoryItem
	for rows.Next() {
		var item model.HistoryItem
		if err := rows.Scan(
			&item.ID,
			&item.JobID,
			&item.ImageName,
			&item.FilePath,
			&item.ModelName,
			&item.Status,
			&item.PositivePrompt,
			&item.NegativePrompt,
			&item.SamplingSteps,
			&item.Seed,
			&item.GuidanceScale,
			&item.VisualFidelity,
			&item.TextConsistency,
			&item.PhysicalPlausibility,
			&item.CompositionAesthetics,
			&item.TotalScore,
			&item.CreatedAt,
		); err != nil {
			return nil, err
		}
		items = append(items, item)
	}
	return items, rows.Err()
}

// ListHistoryPage 联表查询带分页和筛选条件的历史记录。
func (r *AssetRepository) ListHistoryPage(ctx context.Context, query model.HistoryPageQuery) (model.HistoryPageResult, error) {
	if err := r.ensureSchema(ctx); err != nil {
		return model.HistoryPageResult{}, err
	}

	whereSQL, args := buildHistoryWhereClause(query)

	countQuery := `
SELECT COUNT(*)
FROM asset_images i
JOIN asset_image_prompts p ON p.image_id = i.id
JOIN asset_image_scores s ON s.image_id = i.id
` + whereSQL

	var total int
	if err := r.db.QueryRowContext(ctx, countQuery, args...).Scan(&total); err != nil {
		return model.HistoryPageResult{}, err
	}

	offset := (query.Page - 1) * query.PageSize
	dataArgs := append(append([]any{}, args...), query.PageSize, offset)
	rows, err := r.db.QueryContext(ctx, `
SELECT i.id, i.job_id, i.image_name, i.file_path, i.model_name, i.status,
       p.positive_prompt, p.negative_prompt, p.sampling_steps, p.seed, p.guidance_scale,
       s.visual_fidelity, s.text_consistency, s.physical_plausibility, s.composition_aesthetics, s.total_score,
       i.created_at
FROM asset_images i
JOIN asset_image_prompts p ON p.image_id = i.id
JOIN asset_image_scores s ON s.image_id = i.id
`+whereSQL+`
ORDER BY i.id DESC
LIMIT ? OFFSET ?
`, dataArgs...)
	if err != nil {
		return model.HistoryPageResult{}, err
	}
	defer rows.Close()

	items, err := scanHistoryItems(rows)
	if err != nil {
		return model.HistoryPageResult{}, err
	}

	return model.BuildHistoryPageResult(items, query.Page, query.PageSize, total), nil
}

// GetDetail 查询单条资产记录的完整详情。
func (r *AssetRepository) GetDetail(ctx context.Context, id int64) (model.AssetDetail, error) {
	if err := r.ensureSchema(ctx); err != nil {
		return model.AssetDetail{}, err
	}

	var detail model.AssetDetail
	var checkedImagePath sql.NullString
	var explanationJSON sql.NullString
	err := r.db.QueryRowContext(ctx, `
SELECT i.id, i.job_id, i.image_name, i.file_path, i.model_name, i.status, i.created_at, i.updated_at,
       p.positive_prompt, p.negative_prompt, p.sampling_steps, p.seed, p.guidance_scale,
       s.visual_fidelity, s.text_consistency, s.physical_plausibility, s.composition_aesthetics, s.total_score,
       e.checked_image_path, e.explanation_json
FROM asset_images i
JOIN asset_image_prompts p ON p.image_id = i.id
JOIN asset_image_scores s ON s.image_id = i.id
LEFT JOIN asset_image_score_explanations e ON e.image_id = i.id
WHERE i.id = ?
`, id).Scan(
		&detail.Asset.ID,
		&detail.Asset.JobID,
		&detail.Asset.ImageName,
		&detail.Asset.FilePath,
		&detail.Asset.ModelName,
		&detail.Asset.Status,
		&detail.Asset.CreatedAt,
		&detail.Asset.UpdatedAt,
		&detail.Prompt.PositivePrompt,
		&detail.Prompt.NegativePrompt,
		&detail.Prompt.SamplingSteps,
		&detail.Prompt.Seed,
		&detail.Prompt.GuidanceScale,
		&detail.Score.VisualFidelity,
		&detail.Score.TextConsistency,
		&detail.Score.PhysicalPlausibility,
		&detail.Score.CompositionAesthetics,
		&detail.Score.TotalScore,
		&checkedImagePath,
		&explanationJSON,
	)
	if err != nil {
		return model.AssetDetail{}, err
	}
	if checkedImagePath.Valid {
		detail.CheckedImagePath = checkedImagePath.String
	}
	if explanationJSON.Valid && explanationJSON.String != "" {
		detail.ScoreExplanation = []byte(explanationJSON.String)
	}
	return detail, nil
}

func buildHistoryWhereClause(query model.HistoryPageQuery) (string, []any) {
	clauses := make([]string, 0, 4)
	args := make([]any, 0, 4)

	if keyword := strings.TrimSpace(query.PromptKeyword); keyword != "" {
		pattern := "%" + strings.ToLower(keyword) + "%"
		clauses = append(clauses, "(LOWER(p.positive_prompt) LIKE ? OR LOWER(i.image_name) LIKE ?)")
		args = append(args, pattern, pattern)
	}
	if modelName := strings.TrimSpace(query.ModelName); modelName != "" {
		clauses = append(clauses, "LOWER(i.model_name) LIKE ?")
		args = append(args, "%"+strings.ToLower(modelName)+"%")
	}
	if status := strings.TrimSpace(strings.ToLower(query.Status)); status != "" && status != "all" {
		clauses = append(clauses, "LOWER(i.status) = ?")
		args = append(args, status)
	}
	if query.MinTotalScore > 0 {
		clauses = append(clauses, "s.total_score >= ?")
		args = append(args, query.MinTotalScore)
	}

	if len(clauses) == 0 {
		return "", args
	}
	return "\nWHERE " + strings.Join(clauses, " AND "), args
}

func scanHistoryItems(rows *sql.Rows) ([]model.HistoryItem, error) {
	var items []model.HistoryItem
	for rows.Next() {
		var item model.HistoryItem
		if err := rows.Scan(
			&item.ID,
			&item.JobID,
			&item.ImageName,
			&item.FilePath,
			&item.ModelName,
			&item.Status,
			&item.PositivePrompt,
			&item.NegativePrompt,
			&item.SamplingSteps,
			&item.Seed,
			&item.GuidanceScale,
			&item.VisualFidelity,
			&item.TextConsistency,
			&item.PhysicalPlausibility,
			&item.CompositionAesthetics,
			&item.TotalScore,
			&item.CreatedAt,
		); err != nil {
			return nil, err
		}
		items = append(items, item)
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}
	if items == nil {
		items = []model.HistoryItem{}
	}
	return items, nil
}
