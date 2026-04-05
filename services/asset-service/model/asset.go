package model

type Image struct {
	ID        int64  `json:"id"`
	JobID     int64  `json:"job_id"`
	ImageName string `json:"image_name"`
	FilePath  string `json:"file_path"`
	ModelName string `json:"model_name"`
	Status    string `json:"status"`
}

type Prompt struct {
	PositivePrompt string
	NegativePrompt string
	SamplingSteps  int
	Seed           int64
	GuidanceScale  float64
}

type Score struct {
	VisualFidelity        float64
	TextConsistency       float64
	PhysicalPlausibility  float64
	CompositionAesthetics float64
	TotalScore            float64
}

type SaveGenerateResultInput struct {
	JobID                 int64
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
