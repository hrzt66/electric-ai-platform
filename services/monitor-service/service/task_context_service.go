package service

import "context"

// TaskContextService is a minimal placeholder for Task 4 wiring.
// Task 5+ can expand this, but for now we keep it lightweight and optional.
type TaskContextService interface {
	// WithTaskID associates a task id with the context.
	WithTaskID(ctx context.Context, taskID string) context.Context
	// TaskID retrieves a task id from the context.
	TaskID(ctx context.Context) (string, bool)
}

type taskIDKey struct{}

type DefaultTaskContextService struct{}

func NewDefaultTaskContextService() *DefaultTaskContextService { return &DefaultTaskContextService{} }

func (DefaultTaskContextService) WithTaskID(ctx context.Context, taskID string) context.Context {
	if taskID == "" {
		return ctx
	}
	return context.WithValue(ctx, taskIDKey{}, taskID)
}

func (DefaultTaskContextService) TaskID(ctx context.Context) (string, bool) {
	v := ctx.Value(taskIDKey{})
	if v == nil {
		return "", false
	}
	id, ok := v.(string)
	if !ok || id == "" {
		return "", false
	}
	return id, true
}

