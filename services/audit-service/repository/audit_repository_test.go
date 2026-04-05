package repository

import (
	"strings"
	"testing"
)

func TestAuditSchemaStatementsIncludePayloadMigration(t *testing.T) {
	joined := strings.Join(auditSchemaStatements(), "\n")

	if !strings.Contains(joined, "ALTER TABLE audit_task_events") {
		t.Fatal("expected audit schema to include legacy table migration")
	}
	if !strings.Contains(joined, "ADD COLUMN payload_json") {
		t.Fatal("expected audit schema to backfill payload_json column")
	}
}
