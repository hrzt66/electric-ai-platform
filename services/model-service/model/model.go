package model

type RegistryModel struct {
	ID          int64  `json:"id"`
	ModelName   string `json:"model_name"`
	ModelType   string `json:"model_type"`
	ServiceName string `json:"service_name"`
	Status      string `json:"status"`
}
