package repository

import (
	"strings"
	"testing"
)

func TestTaskSchemaStatementsIncludeLegacyColumnMigrations(t *testing.T) {
	joined := strings.Join(taskSchemaStatements(), "\n")

	if !strings.Contains(joined, "ALTER TABLE task_jobs") {
		t.Fatal("expected task schema to include legacy table migration")
	}
	if !strings.Contains(joined, "ADD COLUMN stage") {
		t.Fatal("expected task schema to backfill stage column")
	}
	if !strings.Contains(joined, "ADD COLUMN model_name") {
		t.Fatal("expected task schema to backfill model_name column")
	}
	if !strings.Contains(joined, "ADD COLUMN scoring_model_name") {
		t.Fatal("expected task schema to backfill scoring_model_name column")
	}
}
