package config

import "testing"

func TestLoadBuildsConfigFromEnv(t *testing.T) {
	t.Setenv("APP_NAME", "auth-service")
	t.Setenv("HTTP_PORT", "8081")
	t.Setenv("MYSQL_DSN", "root:root@tcp(localhost:3306)/electric_ai?charset=utf8mb4&parseTime=True&loc=Local")
	t.Setenv("REDIS_ADDR", "localhost:6379")
	t.Setenv("JWT_SECRET", "electric-ai-secret")

	cfg := Load()

	if cfg.AppName != "auth-service" {
		t.Fatalf("expected auth-service, got %s", cfg.AppName)
	}
	if cfg.HTTPPort != "8081" {
		t.Fatalf("expected 8081, got %s", cfg.HTTPPort)
	}
	if cfg.JWTSecret != "electric-ai-secret" {
		t.Fatalf("expected jwt secret to be loaded")
	}
}
