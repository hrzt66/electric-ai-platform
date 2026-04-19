package service

import (
	"context"
	"path/filepath"

	"electric-ai/services/asset-service/model"
)

type Image = model.Image
type Prompt = model.Prompt
type Score = model.Score
type SaveGenerateAssetInput = model.SaveGenerateAssetInput
type SaveGenerateResultsInput = model.SaveGenerateResultsInput
type PersistAssetResult = model.PersistAssetResult
type HistoryItem = model.HistoryItem
type HistoryPageQuery = model.HistoryPageQuery
type HistoryPageResult = model.HistoryPageResult
type AssetDetail = model.AssetDetail

// Repository 定义资产服务依赖的持久化接口。
type Repository interface {
	SaveResults(ctx context.Context, jobID int64, items []PersistAssetResult) ([]HistoryItem, error)
	ListHistory(ctx context.Context) ([]HistoryItem, error)
	ListHistoryPage(ctx context.Context, query HistoryPageQuery) (HistoryPageResult, error)
	GetDetail(ctx context.Context, id int64) (AssetDetail, error)
}

// AssetService 负责把 Python 运行时的评分结果整理成资产服务统一的数据结构。
type AssetService struct {
	repo Repository
}

func NewAssetService(repo Repository) *AssetService {
	return &AssetService{repo: repo}
}

func (s *AssetService) SaveGenerateResults(ctx context.Context, input SaveGenerateResultsInput) ([]HistoryItem, error) {
	// 这里补齐 imageName，避免运行时只返回 filePath 时历史中心无法展示友好文件名。
	items := make([]PersistAssetResult, 0, len(input.Results))
	for _, result := range input.Results {
		imageName := result.ImageName
		if imageName == "" {
			imageName = filepath.Base(result.FilePath)
		}
		items = append(items, PersistAssetResult{
			ImageName:             imageName,
			FilePath:              result.FilePath,
			ModelName:             result.ModelName,
			PositivePrompt:        result.PositivePrompt,
			NegativePrompt:        result.NegativePrompt,
			SamplingSteps:         result.SamplingSteps,
			Seed:                  result.Seed,
			GuidanceScale:         result.GuidanceScale,
			VisualFidelity:        result.VisualFidelity,
			TextConsistency:       result.TextConsistency,
			PhysicalPlausibility:  result.PhysicalPlausibility,
			CompositionAesthetics: result.CompositionAesthetics,
			TotalScore:            result.TotalScore,
			CheckedImagePath:      result.CheckedImagePath,
			ScoreExplanation:      result.ScoreExplanation,
		})
	}

	history, err := s.repo.ListHistory(ctx)
	if err != nil {
		return nil, err
	}

	existingByImageName := make(map[string]HistoryItem)
	for _, item := range history {
		if item.JobID != input.JobID {
			continue
		}
		existingByImageName[item.ImageName] = item
	}

	pending := make([]PersistAssetResult, 0, len(items))
	deduped := make([]HistoryItem, 0, len(items))
	for _, item := range items {
		if existing, ok := existingByImageName[item.ImageName]; ok {
			deduped = append(deduped, existing)
			continue
		}
		pending = append(pending, item)
	}

	if len(pending) == 0 {
		return deduped, nil
	}

	saved, err := s.repo.SaveResults(ctx, input.JobID, pending)
	if err != nil {
		return nil, err
	}
	return append(deduped, saved...), nil
}

func (s *AssetService) ListHistory(ctx context.Context) ([]HistoryItem, error) {
	items, err := s.repo.ListHistory(ctx)
	if err != nil {
		return nil, err
	}
	// 前端统一假设历史列表一定是数组，这里兜底 nil -> []。
	if items == nil {
		return []HistoryItem{}, nil
	}
	return items, nil
}

func (s *AssetService) GetAssetDetail(ctx context.Context, id int64) (AssetDetail, error) {
	return s.repo.GetDetail(ctx, id)
}

func (s *AssetService) ListHistoryPage(ctx context.Context, query HistoryPageQuery) (HistoryPageResult, error) {
	normalized := normalizeHistoryPageQuery(query)
	page, err := s.repo.ListHistoryPage(ctx, normalized)
	if err != nil {
		return HistoryPageResult{}, err
	}
	if page.Items == nil {
		page.Items = []HistoryItem{}
	}
	page.Page = normalized.Page
	page.PageSize = normalized.PageSize
	return page, nil
}

func normalizeHistoryPageQuery(query HistoryPageQuery) HistoryPageQuery {
	if query.Page <= 0 {
		query.Page = 1
	}
	if query.PageSize <= 0 {
		query.PageSize = 10
	}
	if query.PageSize > 100 {
		query.PageSize = 100
	}
	return query
}
