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

func TestRecordTaskEventAppendsAuditEvent(t *testing.T) {
	repo := &memoryEventRepo{}
	svc := NewAuditService(repo)

	err := svc.RecordTaskEvent(context.Background(), 7, "generate.completed", "mock image saved")
	if err != nil {
		t.Fatalf("expected nil error, got %v", err)
	}
	if len(repo.items) != 1 || repo.items[0].JobID != 7 {
		t.Fatalf("unexpected events: %+v", repo.items)
	}
}
