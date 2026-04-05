package service

import (
	"context"

	"electric-ai/services/model-service/model"
)

type RegistryModel = model.RegistryModel

type Repository interface {
	ListActive(ctx context.Context) ([]RegistryModel, error)
}

type ModelService struct {
	repo Repository
}

func NewModelService(repo Repository) *ModelService {
	return &ModelService{repo: repo}
}

func (s *ModelService) ListActive(ctx context.Context) ([]RegistryModel, error) {
	return s.repo.ListActive(ctx)
}
