package model

import (
	"encoding/json"
	"math"
	"time"
)

type Image struct {
	ID        int64     `json:"id"`
	JobID     int64     `json:"job_id"`
	ImageName string    `json:"image_name"`
	FilePath  string    `json:"file_path"`
	ModelName string    `json:"model_name"`
	Status    string    `json:"status"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}

type Prompt struct {
	PositivePrompt string  `json:"positive_prompt"`
	NegativePrompt string  `json:"negative_prompt"`
	SamplingSteps  int     `json:"sampling_steps"`
	Seed           int64   `json:"seed"`
	GuidanceScale  float64 `json:"guidance_scale"`
}

type Score struct {
	VisualFidelity        float64 `json:"visual_fidelity"`
	TextConsistency       float64 `json:"text_consistency"`
	PhysicalPlausibility  float64 `json:"physical_plausibility"`
	CompositionAesthetics float64 `json:"composition_aesthetics"`
	TotalScore            float64 `json:"total_score"`
}

type SaveGenerateAssetInput struct {
	ImageName             string          `json:"image_name"`
	FilePath              string          `json:"file_path"`
	ModelName             string          `json:"model_name"`
	PositivePrompt        string          `json:"positive_prompt"`
	NegativePrompt        string          `json:"negative_prompt"`
	SamplingSteps         int             `json:"sampling_steps"`
	Seed                  int64           `json:"seed"`
	GuidanceScale         float64         `json:"guidance_scale"`
	VisualFidelity        float64         `json:"visual_fidelity"`
	TextConsistency       float64         `json:"text_consistency"`
	PhysicalPlausibility  float64         `json:"physical_plausibility"`
	CompositionAesthetics float64         `json:"composition_aesthetics"`
	TotalScore            float64         `json:"total_score"`
	CheckedImagePath      string          `json:"checked_image_path,omitempty"`
	ScoreExplanation      json.RawMessage `json:"score_explanation,omitempty"`
}

type SaveGenerateResultsInput struct {
	JobID   int64                    `json:"job_id"`
	Results []SaveGenerateAssetInput `json:"results"`
}

type PersistAssetResult struct {
	ImageName             string
	FilePath              string
	ModelName             string
	PositivePrompt        string
	NegativePrompt        string
	SamplingSteps         int
	Seed                  int64
	GuidanceScale         float64
	VisualFidelity        float64
	TextConsistency       float64
	PhysicalPlausibility  float64
	CompositionAesthetics float64
	TotalScore            float64
	CheckedImagePath      string
	ScoreExplanation      json.RawMessage
}

type HistoryItem struct {
	ID                    int64     `json:"id"`
	JobID                 int64     `json:"job_id"`
	ImageName             string    `json:"image_name"`
	FilePath              string    `json:"file_path"`
	ModelName             string    `json:"model_name"`
	Status                string    `json:"status"`
	PositivePrompt        string    `json:"positive_prompt"`
	NegativePrompt        string    `json:"negative_prompt"`
	SamplingSteps         int       `json:"sampling_steps"`
	Seed                  int64     `json:"seed"`
	GuidanceScale         float64   `json:"guidance_scale"`
	VisualFidelity        float64   `json:"visual_fidelity"`
	TextConsistency       float64   `json:"text_consistency"`
	PhysicalPlausibility  float64   `json:"physical_plausibility"`
	CompositionAesthetics float64   `json:"composition_aesthetics"`
	TotalScore            float64   `json:"total_score"`
	CreatedAt             time.Time `json:"created_at"`
}

type HistoryPageQuery struct {
	Page          int     `form:"page" json:"page"`
	PageSize      int     `form:"page_size" json:"page_size"`
	PromptKeyword string  `form:"prompt_keyword" json:"prompt_keyword"`
	ModelName     string  `form:"model_name" json:"model_name"`
	Status        string  `form:"status" json:"status"`
	MinTotalScore float64 `form:"min_total_score" json:"min_total_score"`
}

type HistoryPageResult struct {
	Items      []HistoryItem `json:"items"`
	Page       int           `json:"page"`
	PageSize   int           `json:"page_size"`
	Total      int           `json:"total"`
	TotalPages int           `json:"total_pages"`
}

func BuildHistoryPageResult(items []HistoryItem, page int, pageSize int, total int) HistoryPageResult {
	totalPages := 0
	if pageSize > 0 && total > 0 {
		totalPages = int(math.Ceil(float64(total) / float64(pageSize)))
	}
	return HistoryPageResult{
		Items:      items,
		Page:       page,
		PageSize:   pageSize,
		Total:      total,
		TotalPages: totalPages,
	}
}

type AssetDetail struct {
	Asset            Image           `json:"asset"`
	Prompt           Prompt          `json:"prompt"`
	Score            Score           `json:"score"`
	CheckedImagePath string          `json:"checked_image_path,omitempty"`
	ScoreExplanation json.RawMessage `json:"score_explanation,omitempty"`
}
