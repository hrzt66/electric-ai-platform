package repository

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestModelSchemaStatementsIncludeCatalogExpansion(t *testing.T) {
	joined := strings.Join(modelSchemaStatements(), "\n")

	if !strings.Contains(joined, "ALTER TABLE model_registry") {
		t.Fatal("expected model schema to include legacy table migration")
	}
	if !strings.Contains(joined, "ADD COLUMN display_name") {
		t.Fatal("expected model schema to backfill display_name column")
	}
	if !strings.Contains(joined, "ADD COLUMN local_path") {
		t.Fatal("expected model schema to backfill local_path column")
	}
}

func TestModelSchemaStatementsDeduplicateAndProtectModelName(t *testing.T) {
	joined := strings.Join(modelSchemaStatements(), "\n")

	if !strings.Contains(joined, "uk_model_registry_model_name") {
		t.Fatal("expected model schema to add a unique index for model_name")
	}
	if !strings.Contains(joined, "target.model_name = keeper.model_name") {
		t.Fatal("expected model schema to deduplicate repeated model names before adding unique index")
	}
	if !strings.Contains(joined, "target.id > keeper.id") {
		t.Fatal("expected model schema deduplication to keep the earliest registry row")
	}
}

func TestModelInitScriptsKeepRegistrySeedIdempotent(t *testing.T) {
	schemaPath := filepath.Join("..", "..", "..", "deploy", "mysql", "init", "001_schema.sql")
	schemaContent, err := os.ReadFile(schemaPath)
	if err != nil {
		t.Fatalf("read schema script: %v", err)
	}

	schema := string(schemaContent)
	if !strings.Contains(schema, "UNIQUE KEY uk_model_registry_model_name (model_name)") {
		t.Fatal("expected schema init script to create a unique index for model_name")
	}

	seedPath := filepath.Join("..", "..", "..", "deploy", "mysql", "init", "002_seed.sql")
	seedContent, err := os.ReadFile(seedPath)
	if err != nil {
		t.Fatalf("read seed script: %v", err)
	}

	seed := string(seedContent)
	if !strings.Contains(seed, "ON DUPLICATE KEY UPDATE") {
		t.Fatal("expected seed script to upsert model registry records")
	}
}
