package model

type Job struct {
	ID          int64  `json:"id"`
	JobType     string `json:"job_type"`
	Status      string `json:"status"`
	PayloadJSON string `json:"payload_json"`
}

type CreateGenerateJobInput struct {
	Prompt         string `json:"prompt"`
	NegativePrompt string `json:"negative_prompt"`
	ModelName      string `json:"model_name"`
}
