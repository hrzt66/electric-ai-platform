package model

type RegistryModel struct {
	ID                    int64  `json:"id"`
	ModelName             string `json:"model_name"`
	DisplayName           string `json:"display_name"`
	ModelType             string `json:"model_type"`
	ServiceName           string `json:"service_name"`
	Status                string `json:"status"`
	Description           string `json:"description"`
	DefaultPositivePrompt string `json:"default_positive_prompt"`
	DefaultNegativePrompt string `json:"default_negative_prompt"`
	LocalPath             string `json:"local_path"`
}
