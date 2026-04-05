package model

import "time"

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
	ImageName             string  `json:"image_name"`
	FilePath              string  `json:"file_path"`
	ModelName             string  `json:"model_name"`
	PositivePrompt        string  `json:"positive_prompt"`
	NegativePrompt        string  `json:"negative_prompt"`
	SamplingSteps         int     `json:"sampling_steps"`
	Seed                  int64   `json:"seed"`
	GuidanceScale         float64 `json:"guidance_scale"`
	VisualFidelity        float64 `json:"visual_fidelity"`
	TextConsistency       float64 `json:"text_consistency"`
	PhysicalPlausibility  float64 `json:"physical_plausibility"`
	CompositionAesthetics float64 `json:"composition_aesthetics"`
	TotalScore            float64 `json:"total_score"`
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

type AssetDetail struct {
	Asset  Image  `json:"asset"`
	Prompt Prompt `json:"prompt"`
	Score  Score  `json:"score"`
}
