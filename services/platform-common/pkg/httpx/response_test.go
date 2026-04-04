package httpx

import "testing"

func TestOKBuildsSuccessResponse(t *testing.T) {
	type payload struct {
		ID string `json:"id"`
	}

	resp := OK(payload{ID: "abc"}, "trace-1")

	if resp.Code != 0 {
		t.Fatalf("expected code 0, got %d", resp.Code)
	}
	if resp.Message != "success" {
		t.Fatalf("expected success message, got %s", resp.Message)
	}
	if resp.Data.ID != "abc" {
		t.Fatalf("expected payload id abc, got %s", resp.Data.ID)
	}
	if resp.TraceID != "trace-1" {
		t.Fatalf("expected trace id trace-1, got %s", resp.TraceID)
	}
}
