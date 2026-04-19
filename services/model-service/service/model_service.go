package service

import (
	"context"
	"os"
	"path/filepath"

	"electric-ai/services/model-service/model"
)

type RegistryModel = model.RegistryModel

// Repository 抽象模型目录数据来源，便于后续替换为外部注册中心或缓存层。
type Repository interface {
	ListCatalog(ctx context.Context) ([]RegistryModel, error)
	GetByName(ctx context.Context, modelName string) (RegistryModel, error)
}

// ModelService 负责把静态模型目录与本地运行时状态拼装成前端可用结果。
type ModelService struct {
	repo Repository
}

func NewModelService(repo Repository) *ModelService {
	return &ModelService{repo: repo}
}

// ListModels 会在仓储返回基础目录后，进一步探测本地模型文件是否真的可用。
func (s *ModelService) ListModels(ctx context.Context) ([]RegistryModel, error) {
	items, err := s.repo.ListCatalog(ctx)
	if err != nil {
		return nil, err
	}
	for index := range items {
		items[index] = hydrateStatus(items[index])
	}
	return items, nil
}

func (s *ModelService) GetModel(ctx context.Context, modelName string) (RegistryModel, error) {
	item, err := s.repo.GetByName(ctx, modelName)
	if err != nil {
		return RegistryModel{}, err
	}
	return hydrateStatus(item), nil
}

// hydrateStatus 用实际磁盘内容覆盖注册表中的状态，避免“表里存在但目录为空”误报为可用。
func hydrateStatus(item RegistryModel) RegistryModel {
	if item.LocalPath == "" {
		return item
	}

	if item.ModelName == "electric-score-v1" {
		imageRewardDir := filepath.Join(filepath.Dir(item.LocalPath), "image-reward")
		aestheticDir := filepath.Join(filepath.Dir(item.LocalPath), "aesthetic-predictor")
		if hasLocalModelFiles(imageRewardDir) && hasLocalModelFiles(aestheticDir) {
			item.Status = "available"
			return item
		}
		if item.Status != "experimental" {
			item.Status = "unavailable"
		}
		return item
	}

	if !hasLocalModelFiles(item.LocalPath) {
		if item.Status != "experimental" {
			item.Status = "unavailable"
		}
		return item
	}

	item.Status = "available"
	return item
}

func hasLocalModelFiles(path string) bool {
	entries, err := os.ReadDir(path)
	return err == nil && len(entries) > 0
}
