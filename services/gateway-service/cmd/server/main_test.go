package main

import "testing"

func TestResolveImageCheckDirUsesExplicitEnvWhenProvided(t *testing.T) {
	t.Setenv("IMAGE_OUTPUT_DIR", "/tmp/model/image")
	t.Setenv("IMAGE_CHECK_OUTPUT_DIR", "/tmp/custom/image_check")

	if got := resolveImageCheckDir(); got != "/tmp/custom/image_check" {
		t.Fatalf("expected explicit image check dir, got %s", got)
	}
}

func TestResolveImageCheckDirDerivesSiblingFromImageOutputDir(t *testing.T) {
	t.Setenv("IMAGE_OUTPUT_DIR", "/Users/hrzt/code/project/model/image")
	t.Setenv("IMAGE_CHECK_OUTPUT_DIR", "")

	if got := resolveImageCheckDir(); got != "/Users/hrzt/code/project/model/image_check" {
		t.Fatalf("expected sibling image_check dir, got %s", got)
	}
}
