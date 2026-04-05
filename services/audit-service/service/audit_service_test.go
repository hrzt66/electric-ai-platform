package service

import (
	"context"
	"testing"
)

type memoryEventRepo struct {
	items []TaskEvent
}

func (m *memoryEventRepo) Append(ctx context.Context, item TaskEvent) error {
	m.items = append(m.items, item)
	return nil
}

func (m *memoryEventRepo) ListByJobID(ctx context.Context, jobID int64) ([]TaskEvent, error) {
	filtered := make([]TaskEvent, 0)
	for _, item := range m.items {
		if item.JobID == jobID {
			filtered = append(filtered, item)
		}
	}
	return filtered, nil
}

func TestRecordTaskEventAppendsAuditEvent(t *testing.T) {
	repo := &memoryEventRepo{}
	svc := NewAuditService(repo)

	err := svc.RecordTaskEvent(context.Background(), RecordTaskEventInput{
		EventType: "generate.completed",
		Payload: map[string]any{
			"job_id":     int64(7),
			"model_name": "sd15-electric",
			"message":    "mock image saved",
			"stage":      "generating",
		},
	})
	if err != nil {
		t.Fatalf("expected nil error, got %v", err)
	}
	if len(repo.items) != 1 || repo.items[0].JobID != 7 {
		t.Fatalf("unexpected events: %+v", repo.items)
	}
	if repo.items[0].Message != "mock image saved" {
		t.Fatalf("expected message to be kept, got %+v", repo.items[0])
	}
}

func TestListTaskEventsReturnsJobScopedAuditTrail(t *testing.T) {
	repo := &memoryEventRepo{
		items: []TaskEvent{
			{JobID: 8, EventType: "task.preparing", Message: "queued"},
			{JobID: 8, EventType: "generation.completed", Message: "image saved"},
			{JobID: 9, EventType: "task.failed", Message: "boom"},
		},
	}
	svc := NewAuditService(repo)

	items, err := svc.ListTaskEvents(context.Background(), 8)
	if err != nil {
		t.Fatalf("expected nil error, got %v", err)
	}
	if len(items) != 2 {
		t.Fatalf("expected 2 events, got %d", len(items))
	}
	if items[1].EventType != "generation.completed" {
		t.Fatalf("unexpected events: %+v", items)
	}
}
