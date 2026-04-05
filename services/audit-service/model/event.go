package model

import "time"

type TaskEvent struct {
	ID          int64     `json:"id"`
	JobID       int64     `json:"job_id"`
	EventType   string    `json:"event_type"`
	Message     string    `json:"message"`
	PayloadJSON string    `json:"payload_json"`
	CreatedAt   time.Time `json:"created_at"`
}

type RecordTaskEventInput struct {
	EventType string         `json:"event_type" binding:"required"`
	Payload   map[string]any `json:"payload" binding:"required"`
}
