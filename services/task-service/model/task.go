package model

import "time"

type Job struct {
	ID             int64     `json:"id"`
	JobType        string    `json:"job_type"`
	Status         string    `json:"status"`
	Stage          string    `json:"stage"`
	ErrorMessage   string    `json:"error_message"`
	ModelName      string    `json:"model_name"`
	Prompt         string    `json:"prompt"`
	NegativePrompt string    `json:"negative_prompt"`
	PayloadJSON    string    `json:"payload_json"`
	CreatedAt      time.Time `json:"created_at"`
	UpdatedAt      time.Time `json:"updated_at"`
}

type CreateGenerateJobInput struct {
	Prompt         string  `json:"prompt"`
	NegativePrompt string  `json:"negative_prompt"`
	ModelName      string  `json:"model_name"`
	Seed           int     `json:"seed"`
	Steps          int     `json:"steps"`
	GuidanceScale  float64 `json:"guidance_scale"`
	Width          int     `json:"width"`
	Height         int     `json:"height"`
	NumImages      int     `json:"num_images"`
}

type UpdateJobStatusInput struct {
	Status       string `json:"status" binding:"required"`
	Stage        string `json:"stage" binding:"required"`
	ErrorMessage string `json:"error_message"`
}
