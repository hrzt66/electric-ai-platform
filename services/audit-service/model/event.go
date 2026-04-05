package model

type TaskEvent struct {
	JobID     int64  `json:"job_id"`
	EventType string `json:"event_type"`
	Message   string `json:"message"`
}
